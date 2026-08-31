import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.continuity import REQUIRED_FILES
from omega.experiment_override import enable_experiment_override
from omega.supervisor import AgentBackend, Supervisor, format_supervisor_status, request_stop, start_scheduled_task


class FakeBackend(AgentBackend):
    def __init__(self, outputs=None, mutate=None):
        self.outputs = list(outputs or [{"ok": True, "output": "done"}]); self.calls = 0; self.mutate = mutate
    def available(self): return True, "fake"
    def execute(self, prompt, root):
        self.calls += 1
        if self.mutate: self.mutate(self.calls, root)
        return self.outputs[min(self.calls - 1, len(self.outputs) - 1)]


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.git_patch = patch("omega.continuity._git", return_value={
            "available": False, "branch": None, "dirty": None, "changed_files": None})
        self.git_patch.start()

    def tearDown(self):
        self.git_patch.stop()

    def repository(self, test_code="import sys;sys.exit(0)"):
        temp = tempfile.TemporaryDirectory(); root = Path(temp.name)
        state = (f"---\nproject_name: OMEGA\ncanonical_path: {root.resolve()}\nversion: 0.21.0\nstatus: verified\n"
                 "last_verified: now\ntest_result: recorded\ncurrent_milestone: V0.21\nnext_milestone: V0.22\n---\n# State\n")
        files = {"PROJECT_STATE.md": state, "NEXT_TASK.md": "---\nbaseline_version: 0.21.0\nmilestone: V0.22\nstatus: planned\n---\n# Task\n",
                 "pyproject.toml": '[project]\nname="omega"\nversion="0.21.0"\n'}
        for name in REQUIRED_FILES: files.setdefault(name, f"# {name}\n")
        for name, content in files.items():
            path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding="utf-8")
        config=root/".omega/config.toml"; config.parent.mkdir(parents=True,exist_ok=True)
        config.write_text("autonomous=true\nauto_continue=true\nauto_repair=true\nmax_auto_repair_attempts=2\n"
                          f"test_command=[\"{sys.executable.replace(chr(92), chr(92)*2)}\",\"-c\",\"{test_code}\"]\n",encoding="utf-8")
        return temp, root

    def test_cycle_loads_next_task_runs_tests_and_heartbeats(self):
        temp,root=self.repository()
        try:
            def mutate(call,path):
                if call==1: (path/"NEXT_TASK.md").write_text("---\nbaseline_version: 0.21.0\nmilestone: V0.23\n---\n",encoding="utf-8")
            supervisor=Supervisor(root,FakeBackend(mutate=mutate)); self.assertEqual("CONTINUE",supervisor.run_cycle())
            heartbeat=supervisor.read_heartbeat(); self.assertEqual("PASS",heartbeat["last_test_result"])
            events=(supervisor.log_path).read_text(encoding="utf-8"); self.assertIn("MILESTONE_COMPLETED",events)
            for event in ("TASK_ACCEPTED", "BACKEND_ROUTED", "SESSION_STARTED",
                          "CHECKPOINT_CREATED", "TASK_COMPLETED"):
                self.assertIn(event, events)
            continuity = supervisor.task_continuity.status(supervisor.current_durable_task_id)
            self.assertEqual("TASK_COMPLETED", continuity["task_state"])
            self.assertEqual("PASS", continuity["host_verification"])
            self.assertIsNone(continuity["active_session"])
            self.assertEqual(supervisor.current_durable_task_id, heartbeat["durable_task_id"])
        finally: temp.cleanup()

    def test_heartbeat_performs_zero_subprocess_calls(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root,FakeBackend())
            with patch("omega.supervisor.subprocess.run") as run, patch("omega.supervisor.subprocess.Popen") as popen:
                payload=supervisor.heartbeat("RUNNING",last_test_result="PASS",retry_count=2)
            run.assert_not_called(); popen.assert_not_called()
            self.assertEqual("0.21.0",payload["current_version"])
            self.assertEqual("V0.21",payload["current_milestone"])
            self.assertEqual("V0.22",payload["current_task"])
        finally:
            temp.cleanup()

    def test_test_failure_triggers_bounded_self_repair(self):
        temp,root=self.repository("import pathlib,sys;sys.exit(0 if pathlib.Path('fixed').exists() else 1)")
        try:
            def mutate(call,path):
                if call==1: (path/"attempt").write_text("ok")
                elif call==2: (path/"fixed").write_text("ok")
                else: (path/"NEXT_TASK.md").write_text("---\nbaseline_version: 0.21.0\nmilestone: V0.23\n---\n",encoding="utf-8")
            backend=FakeBackend(mutate=mutate)
            supervisor=Supervisor(root,backend); self.assertEqual("CONTINUE",supervisor.run_cycle())
            self.assertEqual(3,backend.calls); self.assertEqual(1,supervisor.read_heartbeat()["retry_count"])
        finally: temp.cleanup()

    def test_successful_backend_without_project_changes_stops_before_tests(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root,FakeBackend())
            with patch.object(supervisor,"_tests") as tests:
                self.assertEqual("HARD_BLOCKER",supervisor.run_cycle())
            tests.assert_not_called()
            self.assertIn("AGENT_NO_CHANGES",supervisor.log_path.read_text(encoding="utf-8"))
        finally: temp.cleanup()

    def test_sandbox_cannot_run_python_but_host_verification_proceeds(self):
        temp,root=self.repository()
        try:
            blocker="OMEGA_HARD_BLOCKER: Python interpreter is unavailable inside the sandbox; tests cannot run"
            def mutate(call,path):
                if call==1: (path/"implementation.py").write_text("done")
                else: (path/"NEXT_TASK.md").write_text("---\nbaseline_version: 0.21.0\nmilestone: V0.23\n---\n",encoding="utf-8")
            backend=FakeBackend([{"ok":True,"output":blocker},{"ok":True,"returncode":0,"output":"done"}],mutate=mutate)
            supervisor=Supervisor(root,backend)
            with patch.object(supervisor,"_tests",return_value={"passed":True,"returncode":0,"timed_out":False}) as tests:
                self.assertEqual("CONTINUE",supervisor.run_cycle())
            self.assertTrue(tests.called)
            self.assertIn("AGENT_SANDBOX_VERIFICATION_DEFERRED",supervisor.log_path.read_text(encoding="utf-8"))
        finally: temp.cleanup()

    def test_genuine_backend_failure_is_hard_blocker_without_host_tests(self):
        temp,root=self.repository()
        try:
            backend=FakeBackend([{"ok":False,"returncode":2,"output":"authentication failed"}],
                                mutate=lambda call,path:(path/"partial.txt").write_text("partial"))
            supervisor=Supervisor(root,backend)
            with patch.object(supervisor,"_tests") as tests:
                self.assertEqual("HARD_BLOCKER",supervisor.run_cycle())
            tests.assert_not_called()
            continuity=supervisor.task_continuity.status(supervisor.current_durable_task_id)
            self.assertEqual("PARKED",continuity["task_state"])
            self.assertIsNone(continuity["active_session"])
        finally: temp.cleanup()

    def test_experiment_override_resumes_same_auth_required_task_without_rerouting_loop(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root,FakeBackend(mutate=lambda call,path:(path/"implementation.py").write_text("done")))
            task_before=(root/"NEXT_TASK.md").read_text(encoding="utf-8")
            import hashlib
            task_id="omega-" + hashlib.sha256(task_before.encode("utf-8")).hexdigest()[:24]
            supervisor.task_continuity.accept(task_id, "ENGINEERING_TASK", task_before)
            supervisor.task_continuity.route(task_id, "CODEX_BACKEND")
            session=supervisor.task_continuity.start_session(task_id, "CODEX_BACKEND")
            session_id=session.session_id
            supervisor.task_continuity.lose_session(task_id, session_id, "AUTH_REQUIRED")
            enable_experiment_override(root, task_id=task_id, max_runtime_minutes=120)
            with patch.object(supervisor, "_tests", return_value={"passed": True, "returncode": 0, "timed_out": False}):
                self.assertIn(supervisor.run_cycle(), {"CONTINUE", "HARD_BLOCKER"})
            continuity=supervisor.task_continuity.status(task_id)
            self.assertNotEqual("WAIT_AUTH", continuity.get("recovery_state"))
            self.assertIn("EXPERIMENT_OVERRIDE_RESUMED_TASK", supervisor.log_path.read_text(encoding="utf-8"))
        finally: temp.cleanup()

    def test_codex_backend_places_global_options_before_exec(self):
        from omega.supervisor import CodexBackend
        completed=type("Completed",(),{"returncode":0,"stdout":"ok","stderr":""})()
        with patch.object(CodexBackend,"executable",return_value="codex.cmd"), patch("omega.supervisor.subprocess.run",return_value=completed) as run:
            result=CodexBackend().execute("task",Path("C:/repo"))
        self.assertTrue(result["ok"])
        args=run.call_args.args[0]
        self.assertLess(args.index("--ask-for-approval"),args.index("exec"))
        self.assertLess(args.index("--sandbox"),args.index("exec"))
        self.assertTrue(result["claimed_success"])
        self.assertFalse(result["verified_success"])

    def test_claude_backend_is_selectable_but_not_the_default(self):
        from omega.claude_backend import ClaudeCodeBackend
        temp, root = self.repository()
        try:
            self.assertEqual("CODEX_BACKEND", Supervisor(root).backend.backend_id)
            config = root / ".omega" / "config.toml"
            config.write_text(config.read_text(encoding="utf-8") + '\nagent_backend="claude"\n', encoding="utf-8")
            self.assertIsInstance(Supervisor(root).backend, ClaudeCodeBackend)
        finally:
            temp.cleanup()

    def test_approval_and_hard_blocker_pause_and_report(self):
        approval={"request_id":"r1","work_id":"w1","requesting_component":"backend","action":"publish one file",
                  "authority_required":"owner","resource_scope":"one file","external_effects":"public write",
                  "reversibility":"revert commit","blast_radius":"one repository","expiry":"2026-09-01",
                  "kill_conditions":"scope change","verification_requirements":"verify commit"}
        for marker,status in (("OMEGA_APPROVAL_REQUIRED_JSON: "+json.dumps(approval),"PAUSED_FOR_APPROVAL"),
                              ("OMEGA_HARD_BLOCKER: credentials missing","HARD_BLOCKER")):
            temp,root=self.repository()
            try:
                supervisor=Supervisor(root,FakeBackend([{"ok":False,"output":marker}]))
                self.assertEqual(status,supervisor.run_cycle()); self.assertTrue((supervisor.reports/"FINAL_REPORT.md").exists())
                if status=="PAUSED_FOR_APPROVAL": self.assertTrue((supervisor.runtime/"AWAITING_APPROVAL.md").exists())
            finally: temp.cleanup()

    def test_malformed_approval_markers_never_create_authority(self):
        cases=["OMEGA_APPROVAL_REQUIRED: ordinary prompt text",
               "OMEGA_APPROVAL_REQUIRED_JSON: {}",
               "OMEGA_APPROVAL_REQUIRED_JSON: truncated {",
               "quota error with OMEGA_APPROVAL_REQUIRED_JSON: not-json"]
        for output in cases:
            self.assertIsNone(Supervisor._approval_envelope(output))

    def test_single_instance_stale_recovery_stop_and_status(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root,FakeBackend()); supervisor.lock_path.write_text(json.dumps({"pid":999999}),encoding="utf-8")
            with patch("omega.supervisor.Supervisor.process_identity",return_value=None):
                supervisor.acquire(); self.assertTrue(supervisor.lock_path.exists())
                with patch("omega.supervisor.Supervisor.owns_process",return_value=True):
                    with self.assertRaises(RuntimeError): Supervisor(root).acquire()
                supervisor.heartbeat("RUNNING", pid=999999); supervisor.release()
                with patch("omega.supervisor.Supervisor.owns_process",return_value=False), patch("omega.supervisor.task_state",return_value="READY"):
                    result=request_stop(root); status=format_supervisor_status(root)
            self.assertTrue(result["stopped"]); self.assertIn("Status: STOPPED",status)
        finally: temp.cleanup()

    def test_background_start_uses_scheduled_task(self):
        temp,root=self.repository()
        try:
            with patch("omega.supervisor.task_state", return_value="READY"), \
                 patch("omega.supervisor._task_command") as task_command, \
                 patch("omega.supervisor.Supervisor.read_heartbeat", side_effect=[{}, {"pid":4321,"status":"RUNNING"}]), \
                 patch("omega.supervisor.Supervisor._pid_alive", return_value=True):
                task_command.return_value.returncode=0
                self.assertEqual(4321,start_scheduled_task(root))
                task_command.assert_called_with(["/Run", "/TN", "OMEGA_Autonomous_Supervisor"])
        finally: temp.cleanup()

    def test_stale_pid_and_pid_reuse_never_gain_ownership(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root); record={"pid":4444,"runtime_instance_id":"old","process_created_at":"old"}
            supervisor.lock_path.write_text(json.dumps({"pid":4444,"runtime_instance_id":"other","path":str(root)}),encoding="utf-8")
            with patch.object(supervisor,"_pid_alive",return_value=True), patch.object(supervisor,"process_identity",return_value={"executable":sys.executable,"command_line":f"{root} -m omega.runtime.worker","creation_time":"new"}):
                self.assertFalse(supervisor.owns_process(record))
        finally: temp.cleanup()

    def test_safe_stop_never_uses_taskkill_or_recursive_termination(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root); supervisor.heartbeat("RUNNING",pid=5555,runtime_instance_id="wrong")
            with patch("omega.supervisor.task_state",return_value="READY"), patch("omega.supervisor._task_command") as task, \
                 patch("omega.supervisor.Supervisor.owns_process",return_value=False), \
                 patch("omega.supervisor.Supervisor._pid_alive",side_effect=[True,False,False,False,False]), \
                 patch("omega.supervisor.subprocess.run") as run:
                result=request_stop(root)
                self.assertTrue(result["stopped"]); self.assertFalse(result["forced"])
                self.assertTrue(all("taskkill" not in str(call).lower() for call in run.call_args_list))
        finally: temp.cleanup()

    def test_test_timeout_terminates_only_created_test_process(self):
        temp,root=self.repository("import time;time.sleep(5)")
        try:
            supervisor=Supervisor(root,FakeBackend()); supervisor.config["test_timeout_seconds"]=1
            started=time.monotonic(); result=supervisor._tests()
            self.assertTrue(result["timed_out"]); self.assertFalse(result["passed"])
            self.assertLess(time.monotonic()-started,4)
        finally: temp.cleanup()

    def test_heartbeat_continues_during_long_test(self):
        temp,root=self.repository("import time;time.sleep(2)")
        try:
            supervisor=Supervisor(root,FakeBackend()); supervisor.config["test_timeout_seconds"]=5
            with patch.object(supervisor,"heartbeat",wraps=supervisor.heartbeat) as heartbeat:
                self.assertTrue(supervisor._tests()["passed"]); self.assertGreaterEqual(heartbeat.call_count,2)
                self.assertTrue(all(call.args[0]=="TESTING" for call in heartbeat.call_args_list))
        finally: temp.cleanup()

    def test_intentional_runtime_restart_checkpoints_and_exits_75(self):
        temp,root=self.repository()
        try:
            runtime=root/"omega/supervisor.py"; runtime.parent.mkdir(exist_ok=True); runtime.write_text("before",encoding="utf-8")
            backend=FakeBackend(mutate=lambda call,path: runtime.write_text("after",encoding="utf-8"))
            supervisor=Supervisor(root,backend)
            with patch("omega.supervisor.Supervisor.process_identity",return_value=None):
                with self.assertRaises(SystemExit) as exit_info: supervisor.run(once=True)
            self.assertEqual(75,exit_info.exception.code); self.assertEqual("RESTARTING",supervisor.read_heartbeat()["status"])
            self.assertIn("RUNTIME_RESTART_REQUESTED",supervisor.log_path.read_text(encoding="utf-8"))
        finally: temp.cleanup()

    def test_crash_recovery_replaces_dead_checkpoint_without_reset(self):
        temp,root=self.repository()
        try:
            supervisor=Supervisor(root); supervisor.heartbeat_path.write_text(json.dumps({"status":"CRASHED","pid":999999}),encoding="utf-8")
            supervisor.lock_path.write_text(json.dumps({"pid":999999}),encoding="utf-8")
            with patch("omega.supervisor.Supervisor.process_identity",return_value=None):
                supervisor.acquire(); supervisor.release()
            self.assertIn("SUPERVISOR_RECOVERED",supervisor.log_path.read_text(encoding="utf-8"))
        finally: temp.cleanup()


if __name__ == "__main__": unittest.main()
