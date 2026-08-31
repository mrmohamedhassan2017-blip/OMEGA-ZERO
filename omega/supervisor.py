from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
import xml.sax.saxutils as xmlutils
import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .continuity import ROOT, inspect_project, parse_front_matter
from .task_continuity import ContinuityEngine, ContinuityError, TaskContinuityStore


TASK_NAME = "OMEGA_Autonomous_Supervisor"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class AgentBackend(ABC):
    backend_id = "AGENT_BACKEND"
    provider = "UNKNOWN"

    @abstractmethod
    def available(self) -> tuple[bool, str]: ...

    @abstractmethod
    def execute(self, prompt: str, root: Path) -> dict[str, Any]: ...

    # Provider-neutral capability hooks. They are concrete for compatibility
    # with existing lightweight/fake backends; providers may override them.
    def discover(self) -> dict[str, Any]:
        available, detail = self.available()
        return {"backend_id": self.backend_id, "provider": self.provider,
                "available": available, "detail": detail}

    def availability(self) -> dict[str, Any]:
        return self.discover()

    def capabilities(self) -> dict[str, Any]:
        return {}

    def authentication_state(self) -> str:
        return "UNKNOWN"

    def resource_state(self) -> str:
        return "UNKNOWN"

    def cancel(self, run_id: str) -> bool:
        return False

    def health(self) -> dict[str, Any]:
        return self.availability()

    def usage(self) -> dict[str, Any]:
        return {"runs": "UNKNOWN"}

    def result(self, run_id: str) -> dict[str, Any] | None:
        return None

    def cleanup(self, run_id: str) -> bool:
        return True


class CodexBackend(AgentBackend):
    backend_id = "CODEX_BACKEND"
    provider = "OPENAI_CODEX_CLI"
    @staticmethod
    def executable() -> str | None:
        return (shutil.which("codex.cmd") or shutil.which("codex.exe") or shutil.which("codex"))

    def available(self) -> tuple[bool, str]:
        executable = self.executable()
        return (bool(executable), executable or "Codex CLI not found")

    def execute(self, prompt: str, root: Path) -> dict[str, Any]:
        executable = self.executable()
        if not executable:
            return {"ok": False, "output": "OMEGA_HARD_BLOCKER: Codex CLI not found"}
        completed = subprocess.run(
            [executable, "--ask-for-approval", "never", "--sandbox", "workspace-write",
             "exec", "-C", str(root), "--color", "never", "-"],
            input=prompt, text=True, capture_output=True, timeout=3600,
        )
        claimed = completed.returncode == 0
        return {"ok": claimed, "returncode": completed.returncode,
                "output": (completed.stdout + "\n" + completed.stderr)[-20000:],
                "backend_id": self.backend_id, "provider": self.provider,
                "claimed_success": claimed, "verified_success": False,
                "host_verification_required": True}


class Supervisor:
    def __init__(self, root: Path = ROOT, backend: AgentBackend | None = None):
        self.root = root.resolve()
        self.base = self.root / ".omega"
        self.runtime = self.base / "runtime"
        self.logs = self.base / "logs"
        self.reports = self.base / "reports"
        for path in (self.runtime, self.logs, self.reports):
            path.mkdir(parents=True, exist_ok=True)
        self.config = self._config()
        self.backend = backend or self._configured_backend()
        self.lock_path = self.runtime / "supervisor.lock"
        self.stop_path = self.runtime / "STOP"
        self.heartbeat_path = self.runtime / "heartbeat.json"
        self.log_path = self.logs / "events.jsonl"
        self.started_at = now()
        self.runtime_instance_id = uuid.uuid4().hex
        self.process_created_at = self.started_at
        self.cached_metadata = self._load_cached_metadata()
        self.runtime_fingerprint = self._runtime_fingerprint()
        self.task_continuity_store = TaskContinuityStore(self.runtime / "task_continuity")
        self.task_continuity = ContinuityEngine(self.task_continuity_store)
        self.current_durable_task_id: str | None = None
        self.current_session_id: str | None = None

    def _load_cached_metadata(self) -> dict[str, str]:
        """Read repository metadata files only; never invoke an external process."""
        try: state = parse_front_matter(self.root / "PROJECT_STATE.md")
        except ValueError: state = {}
        try: task = parse_front_matter(self.root / "NEXT_TASK.md")
        except ValueError: task = {}
        return {"version": state.get("version", "unknown"),
                "milestone": state.get("current_milestone", "unknown"),
                "task": task.get("milestone", state.get("next_milestone", "unknown"))}

    def reload_metadata(self) -> dict[str, str]:
        self.cached_metadata = self._load_cached_metadata()
        return self.cached_metadata

    def _runtime_fingerprint(self) -> str:
        digest = hashlib.sha256()
        for relative in ("omega/supervisor.py", "omega/runtime/worker.py", "omega/continuity.py",
                         "omega/task_continuity.py", "omega/claude_backend.py"):
            path = self.root / relative
            if path.exists(): digest.update(path.read_bytes())
        return digest.hexdigest()

    def _workspace_snapshot(self) -> dict[str, tuple[int, int]]:
        """Cheap mutation proof; excludes runtime outputs and generated caches."""
        excluded = {".git", ".omega", "data", "work", "__pycache__", ".pytest_cache"}
        snapshot: dict[str, tuple[int, int]] = {}
        for path in self.root.rglob("*"):
            if not path.is_file() or any(part in excluded for part in path.relative_to(self.root).parts):
                continue
            if path.suffix in {".pyc", ".db", ".log"}: continue
            try:
                stat = path.stat(); snapshot[str(path.relative_to(self.root))] = (stat.st_mtime_ns, stat.st_size)
            except OSError: continue
        return snapshot

    def _config(self) -> dict[str, Any]:
        with (self.base / "config.toml").open("rb") as handle:
            return tomllib.load(handle)

    def _configured_backend(self) -> AgentBackend:
        selected = str(self.config.get("agent_backend", "codex")).strip().lower()
        if selected == "codex":
            return CodexBackend()
        if selected in {"claude", "claude_code"}:
            from .claude_backend import ClaudeCodeBackend
            return ClaudeCodeBackend(
                self.root, history_path=self.logs / "claude_backend_history.jsonl"
            )
        raise ValueError(f"unsupported agent_backend: {selected}")

    def event(self, kind: str, **data: Any) -> None:
        if self.log_path.exists() and self.log_path.stat().st_size > int(self.config.get("log_max_bytes", 1048576)):
            rotated = self.logs / "events.1.jsonl"
            if rotated.exists(): rotated.unlink()
            self.log_path.replace(rotated)
        record = {"timestamp": now(), "event": kind, **data}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False

        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

                handle = kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION,
                    False,
                    pid,
                )
                if not handle:
                    return False

                try:
                    exit_code = wintypes.DWORD()
                    if not kernel32.GetExitCodeProcess(
                        handle, ctypes.byref(exit_code)
                    ):
                        return False
                    return exit_code.value == STILL_ACTIVE
                finally:
                    kernel32.CloseHandle(handle)
            except (OSError, AttributeError, ValueError):
                return False

        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def process_identity(pid: int) -> dict[str, Any] | None:
        if pid <= 0 or os.name != "nt": return None
        script = (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' -ErrorAction SilentlyContinue; "
                  "if($null -ne $p){[pscustomobject]@{executable=$p.ExecutablePath;command_line=$p.CommandLine;creation_time=$p.CreationDate.ToString('o')}|ConvertTo-Json -Compress}")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = None
        try:
            process = subprocess.Popen(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, creationflags=flags)
            stdout, _ = process.communicate(timeout=2)
            return json.loads(stdout) if stdout.strip() else None
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return None
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                try:
                    process.communicate(timeout=1)
                except subprocess.SubprocessError:
                    try:
                        process.wait(timeout=1)
                    except subprocess.SubprocessError:
                        pass

    def owns_process(self, record: dict[str, Any]) -> bool:
        pid = int(record.get("pid", 0))
        if not self._pid_alive(pid): return False
        identity = self.process_identity(pid)
        if not identity: return False
        try: executable_ok = Path(identity.get("executable", "")).resolve() == Path(sys.executable).resolve()
        except OSError: executable_ok = False
        command = identity.get("command_line") or ""
        creation = record.get("process_created_at")
        creation_ok = not creation or creation == identity.get("creation_time")
        lock = {}
        try: lock = json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): pass
        instance_ok = bool(record.get("runtime_instance_id")) and record.get("runtime_instance_id") == lock.get("runtime_instance_id")
        return executable_ok and "omega.runtime.worker" in command and str(self.root).lower() in str(lock.get("path", "")).lower() and creation_ok and instance_ok

    def acquire(self) -> None:
        previous_heartbeat = self.read_heartbeat()
        if self.lock_path.exists():
            try: existing = json.loads(self.lock_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): existing = {}
            if self._pid_alive(int(existing.get("pid", 0))):
                if self.owns_process({**previous_heartbeat, **existing}):
                    raise RuntimeError(f"supervisor already running with PID {existing['pid']}")
                raise RuntimeError(f"live PID {existing['pid']} has an unverified supervisor lock; refusing unsafe recovery")
            self.event("SUPERVISOR_RECOVERED", stale_lock=existing)
            self.lock_path.unlink(missing_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        own = self.process_identity(os.getpid()) or {}
        self.process_created_at = own.get("creation_time", self.started_at)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at": self.started_at, "process_created_at": self.process_created_at,
                       "runtime_instance_id": self.runtime_instance_id, "path": str(self.root)}, handle)
        if previous_heartbeat.get("status") in {"RUNNING", "TESTING", "REPAIRING", "CRASHED", "RESTARTING"}:
            self.event("SUPERVISOR_RECOVERED", previous_status=previous_heartbeat.get("status"), checkpoint="heartbeat.json")

    def release(self) -> None:
        self.lock_path.unlink(missing_ok=True)

    def heartbeat(self, status: str, **extra: Any) -> dict[str, Any]:
        previous = self.read_heartbeat()
        continuity: dict[str, Any] = {}
        if self.current_durable_task_id:
            try:
                current = self.task_continuity.status(self.current_durable_task_id)
                continuity = {
                    "durable_task_id": current["task_id"],
                    "active_session_id": current["active_session"],
                    "last_checkpoint": current["last_checkpoint"],
                    "blocker_class": current["blocker"],
                    "recovery_state": current["recovery_strategy"],
                }
            except ContinuityError:
                continuity = {"durable_task_id": self.current_durable_task_id,
                              "recovery_state": "CONTINUITY_RECORD_UNAVAILABLE"}
        payload = {"status": status, "pid": os.getpid(), "started_at": previous.get("started_at", self.started_at),
                   "process_created_at": self.process_created_at, "runtime_instance_id": self.runtime_instance_id,
                   "last_heartbeat": now(), "current_version": self.cached_metadata["version"],
                   "current_milestone": self.cached_metadata["milestone"], "current_task": self.cached_metadata["task"],
                   "last_test_result": previous.get("last_test_result"), "retry_count": previous.get("retry_count", 0),
                   "blocker": None, "approval_required": False, **continuity, **extra}
        temp = self.heartbeat_path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(self.heartbeat_path)
        return payload

    def read_heartbeat(self) -> dict[str, Any]:
        try: return json.loads(self.heartbeat_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return {}

    def _prompt(self, repair: str | None = None) -> str:
        task = (self.root / "NEXT_TASK.md").read_text(encoding="utf-8")
        base = ("You are the OMEGA autonomous execution backend. Read PROJECT_STATE.md, NEXT_TASK.md, "
                ".ai/EXECUTOR.md and .ai/RULES.md. Work only in this repository. Implement the current NEXT_TASK. "
                "Do not run Python or tests: the trusted host worker performs verification after you return. Do not update "
                "milestone/version state before host verification. Preserve existing work and never use destructive git reset. If human approval "
                "is required, output one line beginning OMEGA_APPROVAL_REQUIRED_JSON: followed by a JSON object containing "
                "request_id, work_id, requesting_component, action, authority_required, resource_scope, external_effects, "
                "reversibility, blast_radius, expiry, kill_conditions, and verification_requirements. If impossible in this environment, "
                "output OMEGA_HARD_BLOCKER: followed by the exact blocker. Do not expose credentials.\n\n")
        return base + (f"Repair the following verified failure first:\n{repair}\n\n" if repair else "") + task

    @staticmethod
    def _sandbox_verification_only(reason: str) -> bool:
        value = reason.lower()
        verification = any(term in value for term in ("python", "test", "verification", "release gate"))
        environment = any(term in value for term in ("sandbox", "path", "interpreter", "outside the permitted workspace", "unavailable"))
        return verification and environment

    def _completion_prompt(self, test_result: dict[str, Any]) -> str:
        return ("Host verification passed for the implemented NEXT_TASK. Do not change application code and do not run tests. "
                "Update only PROJECT_STATE.md, CHANGELOG.md, PROGRESS.md, ROADMAP.md when needed, and NEXT_TASK.md. "
                "Mark the milestone complete only if its repository Definition of Done is satisfied, preserve honest evidence, "
                "select the next explicit roadmap milestone, and keep version metadata consistent. Host result: "
                f"returncode={test_result.get('returncode')}, timed_out={test_result.get('timed_out')}.\n\n" +
                (self.root / "NEXT_TASK.md").read_text(encoding="utf-8"))

    @staticmethod
    def _approval_envelope(output: str) -> dict[str, Any] | None:
        prefix = "OMEGA_APPROVAL_REQUIRED_JSON:"
        lines = [line.strip() for line in output.splitlines() if line.strip().startswith(prefix)]
        if len(lines) != 1: return None
        try: value = json.loads(lines[0][len(prefix):].strip())
        except json.JSONDecodeError: return None
        required = {"request_id", "work_id", "requesting_component", "action", "authority_required",
                    "resource_scope", "external_effects", "reversibility", "blast_radius", "expiry",
                    "kill_conditions", "verification_requirements"}
        if not isinstance(value, dict) or not required.issubset(value): return None
        if any(value.get(key) in (None, "", [], {}) for key in required): return None
        return value

    def _record_host_verification(self, test_result: dict[str, Any]) -> None:
        """Persist host acceptance without requiring the sandbox backend to edit files."""
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        progress = self.root / "PROGRESS.md"
        marker = f"Host verification: {stamp} — returncode={test_result.get('returncode')}, all tests passed."
        text = progress.read_text(encoding="utf-8") if progress.exists() else "# OMEGA Progress\n"
        if marker not in text:
            progress.write_text(text.rstrip() + "\n\n" + marker + "\n", encoding="utf-8")
        state = self.root / "PROJECT_STATE.md"
        if state.exists():
            value = state.read_text(encoding="utf-8")
            value = re.sub(r"test_result:\s*[^\n]+", "test_result: host verification passed", value, count=1)
            value = re.sub(r"last_verified:\s*[^\n]+", f"last_verified: {stamp}", value, count=1)
            state.write_text(value, encoding="utf-8")

    def _tests(self) -> dict[str, Any]:
        command = list(self.config.get("test_command", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]))
        if command and command[0] == "python": command[0] = sys.executable
        timeout = int(self.config.get("test_timeout_seconds", 300)); self.event("HOST_TEST_STARTED", command=command)
        self.heartbeat("TESTING")
        process = subprocess.Popen(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        deadline = time.monotonic() + timeout; timed_out = False
        while process.poll() is None and time.monotonic() < deadline:
            if self.stop_path.exists():
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
                stdout, stderr = process.communicate()
                return {"passed": False, "stopped": True, "returncode": process.returncode,
                        "output": (stdout + "\n" + stderr)[-12000:], "timed_out": False}
            self.heartbeat("TESTING"); time.sleep(min(1, max(.05, deadline - time.monotonic())))
        if process.poll() is None:
            timed_out = True; process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        stdout, stderr = process.communicate(); output = (stdout + "\n" + stderr)[-12000:]
        result = {"passed": process.returncode == 0 and not timed_out, "returncode": process.returncode,
                  "output": output, "timed_out": timed_out}
        self.event("HOST_TEST_PASSED" if result["passed"] else "HOST_TEST_FAILED", returncode=process.returncode, timed_out=timed_out)
        return result

    def _execute_backend(self, prompt: str, status: str = "RUNNING") -> dict[str, Any]:
        finished = threading.Event()
        def pulse() -> None:
            while not finished.wait(5):
                try: self.heartbeat(status)
                except OSError: pass
        thread = threading.Thread(target=pulse, daemon=True); thread.start()
        try: return self.backend.execute(prompt, self.root)
        finally: finished.set(); thread.join(timeout=1)

    def _pause(self, status: str, reason: str, approval: bool = False) -> None:
        if approval:
            (self.runtime / "AWAITING_APPROVAL.md").write_text(
                "# Approval required\n\n## What OMEGA wants to do\n" + reason +
                "\n\n## Why\nRequired to continue the current milestone.\n\n## Risk\nRequires human review.\n"
                "\n## Cost if any\nUnknown unless stated above.\n\n## Files/systems affected\nSee request above.\n"
                "\n## Options\nApprove, reject, or provide a safer alternative.\n\n## Recommended choice\nReview before approval.\n", encoding="utf-8")
        self.heartbeat(status, blocker=reason if not approval else None, approval_required=approval)
        self.event("APPROVAL_REQUIRED" if approval else "HARD_BLOCKER", reason=reason)
        self._final_report(status, reason)

    def _final_report(self, outcome: str, reason: str = "") -> None:
        project = inspect_project(self.root)
        hb = self.read_heartbeat()
        (self.reports / "FINAL_REPORT.md").write_text(
            f"# OMEGA Supervisor Report\n\n- Starting version: {project['version']}\n- Final verified version: {project['version']}\n"
            f"- Outcome: {outcome}\n- Current milestone: {project['current_milestone']}\n- Tests: {hb.get('last_test_result')}\n"
            f"- Auto-repairs: {hb.get('retry_count', 0)}\n- Remaining issue: {reason or 'None'}\n"
            f"- Repository state: {project['continuity']}\n- Recommended next phase: {project['next_milestone']}\n", encoding="utf-8")
        message = "NO USER ACTION REQUIRED" if not reason else reason
        (self.reports / "NEXT_USER_MESSAGE.txt").write_text(message, encoding="utf-8")

    def run_cycle(self) -> str:
        project = inspect_project(self.root)
        if not project["ready_to_continue"]:
            self._pause("HARD_BLOCKER", "; ".join(project["errors"])); return "HARD_BLOCKER"
        available, detail = self.backend.available()
        if not available:
            self._pause("HARD_BLOCKER", f"AgentBackend unavailable: {detail}"); return "HARD_BLOCKER"
        self.reload_metadata()
        task_before = (self.root / "NEXT_TASK.md").read_text(encoding="utf-8")
        durable_task_id = "omega-" + hashlib.sha256(task_before.encode("utf-8")).hexdigest()[:24]
        durable = self.task_continuity.accept(
            durable_task_id, "ENGINEERING_TASK", task_before,
            authority_envelope_id=hashlib.sha256(
                b"OMEGA_INTERNAL_ENGINEERING_NO_EXTERNAL_WRITE_NO_FINANCIAL_AUTHORITY"
            ).hexdigest(),
        )
        self.current_durable_task_id = durable_task_id
        if durable.state in {"HOST_VERIFIED", "TASK_COMPLETED"}:
            self.event("TASK_ALREADY_VERIFIED", durable_task_id=durable_task_id)
            self.heartbeat("PARKED", blocker=None)
            return "PARKED"
        backend_id = str(getattr(self.backend, "backend_id", type(self.backend).__name__))
        if durable.state == "PARKED" and durable.blocker_class == "AUTH_REQUIRED":
            from .experiment_override import evaluate_experiment_authority
            override = evaluate_experiment_authority(
                self.root, action="execute internal engineering task", task_id=durable_task_id
            )
            if override.get("allowed"):
                durable.state = "TASK_ACCEPTED"
                durable.blocker_class = None
                durable.recovery_state = "RESUME_EXPERIMENT"
                durable.next_trigger = "EXPERIMENT_OVERRIDE_ACTIVATED"
                durable.authority_status = "EXPERIMENT_AUTHORIZED"
                durable = self.task_continuity_store.save_task(durable, expected_revision=durable.revision)
                self.event("EXPERIMENT_OVERRIDE_RESUMED_TASK", durable_task_id=durable_task_id,
                           authority_source="EXPERIMENT_OVERRIDE")
        self.task_continuity.route(durable_task_id, backend_id)
        session = self.task_continuity.start_session(durable_task_id, backend_id)
        self.current_session_id = session.session_id
        initial_checkpoint = self.task_continuity.checkpoint(
            durable_task_id, session.session_id, completed_steps=[],
            next_action="EXECUTE_BACKEND", repository_root=self.root,
        )
        self.event("TASK_ACCEPTED", durable_task_id=durable_task_id)
        self.event("BACKEND_ROUTED", durable_task_id=durable_task_id, backend=backend_id)
        self.event("SESSION_STARTED", durable_task_id=durable_task_id,
                   session_id=session.session_id, backend=backend_id)
        self.event("CHECKPOINT_CREATED", durable_task_id=durable_task_id,
                   checkpoint_id=initial_checkpoint.checkpoint_id)
        self.heartbeat("RUNNING", retry_count=0); self.event("NEXT_TASK_LOADED"); self.event("AGENT_STARTED")
        workspace_before = self._workspace_snapshot()
        result = self._execute_backend(self._prompt())
        self.task_continuity.bind_provider_session(
            durable_task_id, session.session_id,
            provider_session_id=result.get("run_id"), pid=result.get("pid"),
        )
        output = result.get("output", "")
        workspace_after = self._workspace_snapshot()
        changed_files = sorted(set(workspace_before) ^ set(workspace_after) |
                               {name for name in workspace_before.keys() & workspace_after.keys()
                                if workspace_before[name] != workspace_after[name]})
        self.event("AGENT_COMPLETED", backend=type(self.backend).__name__, ok=bool(result.get("ok")),
                   returncode=result.get("returncode"), changed_files=changed_files)
        if changed_files: self.event("CHANGES_DETECTED", files=changed_files)
        approval = self._approval_envelope(output)
        if approval:
            self.task_continuity.lose_session(durable_task_id, session.session_id, "AUTHORITY_BLOCKED")
            self._pause("PAUSED_FOR_APPROVAL", json.dumps(approval, ensure_ascii=False, sort_keys=True), True); return "PAUSED_FOR_APPROVAL"
        backend_blocker = output.split("OMEGA_HARD_BLOCKER:", 1)[1].strip() if "OMEGA_HARD_BLOCKER:" in output else ""
        deferred_verification = bool(changed_files and backend_blocker and self._sandbox_verification_only(backend_blocker))
        if deferred_verification:
            self.event("AGENT_SANDBOX_VERIFICATION_DEFERRED", reason=backend_blocker[-2000:])
        elif backend_blocker:
            self.task_continuity.lose_session(durable_task_id, session.session_id, backend_blocker)
            self._pause("HARD_BLOCKER", backend_blocker); return "HARD_BLOCKER"
        if not result.get("ok") and not deferred_verification:
            reason = output.strip()[-2000:] or f"AgentBackend exited with code {result.get('returncode')}"
            self.task_continuity.lose_session(
                durable_task_id, session.session_id,
                str(result.get("failure_class") or reason),
            )
            self._pause("HARD_BLOCKER", f"AgentBackend failed: {reason}"); return "HARD_BLOCKER"
        if not changed_files:
            self.event("AGENT_NO_CHANGES", backend=type(self.backend).__name__)
            self.task_continuity.lose_session(durable_task_id, session.session_id, "UNKNOWN_BLOCKER")
            self._pause("HARD_BLOCKER", "AgentBackend completed without implementing or changing the current NEXT_TASK")
            return "HARD_BLOCKER"
        material_checkpoint = self.task_continuity.checkpoint(
            durable_task_id, session.session_id,
            completed_steps=["BACKEND_CHANGES_DETECTED"], next_action="HOST_VERIFY",
            repository_root=self.root,
            expected_diff={name: "CHANGED" for name in changed_files},
        )
        self.event("CHECKPOINT_CREATED", durable_task_id=durable_task_id,
                   checkpoint_id=material_checkpoint.checkpoint_id)
        tests = self._tests(); attempts = 0
        if tests.get("stopped"):
            self.task_continuity.lose_session(durable_task_id, session.session_id, "PROCESS_EXITED")
            return "STOPPED"
        while not tests["passed"] and self.config.get("auto_repair", True) and attempts < int(self.config.get("max_auto_repair_attempts", 5)):
            attempts += 1; self.heartbeat("REPAIRING", retry_count=attempts, last_test_result="FAIL")
            self.event("AGENT_REPAIR_STARTED", attempt=attempts)
            repair_before = self._workspace_snapshot()
            repaired = self._execute_backend(self._prompt(tests["output"]), "REPAIRING")
            repair_after = self._workspace_snapshot()
            repair_changes = sorted(set(repair_before) ^ set(repair_after) |
                                    {name for name in repair_before.keys() & repair_after.keys()
                                     if repair_before[name] != repair_after[name]})
            self.event("AGENT_COMPLETED", backend=type(self.backend).__name__, ok=bool(repaired.get("ok")),
                       returncode=repaired.get("returncode"), changed_files=repair_changes, repair_attempt=attempts)
            if not repair_changes:
                self.event("AGENT_NO_CHANGES", repair_attempt=attempts)
                self._pause("HARD_BLOCKER", f"Agent repair attempt {attempts} made no repository changes")
                return "HARD_BLOCKER"
            self.event("CHANGES_DETECTED", files=repair_changes, repair_attempt=attempts)
            tests = self._tests()
            if tests.get("stopped"):
                self.task_continuity.lose_session(durable_task_id, session.session_id, "PROCESS_EXITED")
                return "STOPPED"
            if tests["passed"]: self.event("AGENT_REPAIR_SUCCEEDED", attempt=attempts)
        if not tests["passed"]:
            self.task_continuity.host_verified(durable_task_id, session.session_id, False)
            self._pause("HARD_BLOCKER", f"tests failed after {attempts} repair attempt(s)"); return "HARD_BLOCKER"
        self.task_continuity.host_verified(durable_task_id, session.session_id, True)
        task_after = (self.root / "NEXT_TASK.md").read_text(encoding="utf-8")
        if task_after == task_before:
            finalize_before = self._workspace_snapshot()
            self.event("MILESTONE_FINALIZATION_STARTED")
            finalized = self._execute_backend(self._completion_prompt(tests))
            finalize_after = self._workspace_snapshot()
            finalize_changes = sorted(set(finalize_before) ^ set(finalize_after) |
                                      {name for name in finalize_before.keys() & finalize_after.keys()
                                       if finalize_before[name] != finalize_after[name]})
            self.event("AGENT_COMPLETED", backend=type(self.backend).__name__, ok=bool(finalized.get("ok")),
                       returncode=finalized.get("returncode"), changed_files=finalize_changes, phase="finalization")
            if not finalized.get("ok") or not finalize_changes:
                self.event("HOST_STATE_RECORDED", reason="backend finalization unavailable")
                self._record_host_verification(tests)
                task_after = task_before
            else:
                forbidden = [name for name in finalize_changes if name not in {"PROJECT_STATE.md", "CHANGELOG.md", "PROGRESS.md", "ROADMAP.md", "NEXT_TASK.md"}]
                if forbidden:
                    self._pause("HARD_BLOCKER", "Finalization changed application files after host verification: " + ", ".join(forbidden))
                    return "HARD_BLOCKER"
                task_after = (self.root / "NEXT_TASK.md").read_text(encoding="utf-8")
                if task_after == task_before:
                    self.event("HOST_STATE_RECORDED", reason="backend did not advance milestone")
                    self._record_host_verification(tests)
        self.reload_metadata()
        self.task_continuity.complete(durable_task_id, session.session_id)
        self.event("TASK_COMPLETED", durable_task_id=durable_task_id,
                   session_id=session.session_id)
        self.heartbeat("RUNNING", retry_count=attempts, last_test_result="PASS")
        if task_after != task_before: self.event("MILESTONE_COMPLETED"); self.event("NEXT_TASK_LOADED")
        return "CONTINUE"

    def run(self, once: bool = False) -> None:
        self.acquire(); self.stop_path.unlink(missing_ok=True)
        try:
            self.heartbeat("RUNNING"); self.event("SUPERVISOR_STARTED")
            while not self.stop_path.exists():
                outcome = self.run_cycle()
                if self._runtime_fingerprint() != self.runtime_fingerprint:
                    self.heartbeat("RESTARTING", blocker=None)
                    self.event("RUNTIME_RESTART_REQUESTED", reason="runtime code changed", checkpoint="heartbeat.json")
                    raise SystemExit(75)
                if once or outcome != "CONTINUE" or not self.config.get("auto_continue", True): break
                time.sleep(max(1, int(self.config.get("poll_seconds", 30))))
            if self.stop_path.exists(): self.heartbeat("STOPPED"); self.event("SUPERVISOR_STOPPED")
        except Exception as exc:
            self._pause("HARD_BLOCKER", f"supervisor crash: {type(exc).__name__}: {exc}")
            raise
        finally:
            self.release()


def _task_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["schtasks", *args], capture_output=True, text=True, timeout=30)


def task_state() -> str:
    if os.name != "nt": return "UNSUPPORTED"
    script = (f"$t=Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue; "
              "if($null -eq $t){'NOT_INSTALLED'}else{$t.State.ToString().ToUpperInvariant()}")
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                            capture_output=True, text=True, timeout=20)
    return result.stdout.strip() or "UNKNOWN"


def start_scheduled_task(root: Path = ROOT) -> int:
    if task_state() == "NOT_INSTALLED": raise RuntimeError("Scheduled Task is not installed; run supervisor install")
    supervisor = Supervisor(root); current = supervisor.read_heartbeat()
    if current.get("status") in {"RUNNING", "REPAIRING"} and supervisor._pid_alive(int(current.get("pid", 0))):
        raise RuntimeError(f"supervisor already running with PID {current['pid']}")
    supervisor.stop_path.unlink(missing_ok=True)
    result = _task_command(["/Run", "/TN", TASK_NAME])
    if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip())
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        heartbeat = supervisor.read_heartbeat(); pid = int(heartbeat.get("pid", 0))
        if heartbeat.get("status") in {"RUNNING", "REPAIRING"} and supervisor._pid_alive(pid): return pid
        time.sleep(.25)
    raise RuntimeError(f"Scheduled Task started but no live RUNNING heartbeat appeared; task state={task_state()}")


def install_task(root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    if os.name != "nt": raise RuntimeError("install is currently supported through Windows Task Scheduler")
    root = root.resolve(); supervisor = Supervisor(root)
    python = Path(sys.executable).resolve()
    user = subprocess.run(["whoami"], capture_output=True, text=True, check=True).stdout.strip()
    esc = xmlutils.escape
    xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>OMEGA Autonomous Supervisor</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{esc(user)}</UserId></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{esc(user)}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>true</Hidden><RunOnlyIfIdle>false</RunOnlyIfIdle><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><Priority>7</Priority><RestartOnFailure><Interval>PT1M</Interval><Count>5</Count></RestartOnFailure></Settings>
  <Actions Context="Author"><Exec><Command>{esc(str(python))}</Command><Arguments>-m omega.runtime.worker</Arguments><WorkingDirectory>{esc(str(root))}</WorkingDirectory></Exec></Actions>
</Task>'''
    xml_path = supervisor.runtime / "scheduled-task.xml"
    xml_path.write_text(xml, encoding="utf-16")
    return _task_command(["/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"])


def uninstall_task() -> subprocess.CompletedProcess[str]:
    if os.name != "nt": raise RuntimeError("uninstall is currently supported through Windows Task Scheduler")
    return _task_command(["/Delete", "/TN", TASK_NAME, "/F"])


def request_stop(root: Path = ROOT) -> dict[str, Any]:
    supervisor = Supervisor(root)
    supervisor.stop_path.write_text(now(), encoding="utf-8")
    current = supervisor.read_heartbeat()
    pid = int(current.get("pid", 0))
    owned = supervisor.owns_process(current)
    if current:
        current.update({"status": "STOPPING", "last_heartbeat": now()})
        temp = supervisor.heartbeat_path.with_suffix(".tmp")
        temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(supervisor.heartbeat_path)
    deadline = time.monotonic() + 10
    while pid and supervisor._pid_alive(pid) and time.monotonic() < deadline:
        time.sleep(.2)
    task_ended = False; forced = False
    if pid and supervisor._pid_alive(pid) and os.name == "nt" and task_state() not in {"NOT_INSTALLED", "UNSUPPORTED"}:
        _task_command(["/End", "/TN", TASK_NAME]); task_ended = True
        deadline = time.monotonic() + 5
        while supervisor._pid_alive(pid) and time.monotonic() < deadline: time.sleep(.2)
    if pid and supervisor._pid_alive(pid) and owned:
        if os.name == "nt":
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            f"Stop-Process -Id {pid} -Force"], capture_output=True, timeout=15)
        else: os.kill(pid, 15)
        forced = True
    alive = bool(pid and supervisor._pid_alive(pid))
    if not alive:
        supervisor.lock_path.unlink(missing_ok=True); supervisor.stop_path.unlink(missing_ok=True)
        current.update({"status": "STOPPED", "last_heartbeat": now(), "blocker": None, "approval_required": False})
    else:
        current.update({"status": "STOPPING", "blocker": "process still alive; forced termination refused because ownership was not verified"})
    temp = supervisor.heartbeat_path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"); temp.replace(supervisor.heartbeat_path)
    return {"stopped": not alive, "pid": pid or None, "task_ended": task_ended, "forced": forced, "ownership_verified": owned}


def format_supervisor_status(root: Path = ROOT) -> str:
    supervisor = Supervisor(root); hb = supervisor.read_heartbeat()
    pid = int(hb.get("pid", 0)); alive = supervisor._pid_alive(pid)
    status = hb.get("status", "STOPPED")
    if status in {"RUNNING", "TESTING", "REPAIRING", "STOPPING"} and not alive: status = "CRASHED"
    scheduled = task_state()
    return "\n".join(("OMEGA AUTONOMOUS SUPERVISOR", "", f"Status: {status}", f"Scheduled Task: {scheduled}",
                       f"Version: {hb.get('current_version', 'unknown')}",
                       f"Current milestone: {hb.get('current_milestone', 'unknown')}",
                       f"Current task: {hb.get('current_task', 'unknown')}",
                       f"Last heartbeat: {hb.get('last_heartbeat', 'never')}",
                       f"Tests: {hb.get('last_test_result', 'not run')}",
                       f"Auto-repairs: {hb.get('retry_count', 0)}",
                       f"Approval required: {'YES' if hb.get('approval_required') else 'NO'}",
                       f"Hard blocker: {hb.get('blocker') or 'NONE'}", "",
                       f"AUTONOMY: {'ACTIVE' if status in {'RUNNING','TESTING','REPAIRING'} and alive else 'INACTIVE'}"))

