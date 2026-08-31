from __future__ import annotations

import json
import multiprocessing
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.task_continuity import (
    ContinuityEngine,
    ContinuityError,
    IntegrityError,
    OwnershipError,
    ReconciliationError,
    TaskContinuityStore,
    classify_blocker,
    recovery_strategy,
)


def _multiprocess_cas_worker(store_root, revision, state, ready, start, results):
    store = TaskContinuityStore(Path(store_root))
    candidate = store.load_task("task-1")
    candidate.revision = revision
    candidate.state = state
    ready.put(state)
    start.wait(5)
    try:
        store.save_task(candidate, expected_revision=revision)
        results.put("PASS")
    except OwnershipError:
        results.put("REJECTED")


class TaskContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.store = TaskContinuityStore(self.root / "continuity")
        self.engine = ContinuityEngine(self.store)
        self.authority = "authority-envelope-1"

    def tearDown(self):
        self.temp.cleanup()

    def _task(self, task_id="task-1"):
        return self.engine.accept(
            task_id, "CODE_REPAIR", "repair bounded fixture",
            authority_envelope_id=self.authority,
        )

    def _session(self, task_id="task-1", session_id="session-1"):
        self._task(task_id)
        self.engine.route(task_id, "CLAUDE_CODE_BACKEND")
        return self.engine.start_session(
            task_id, "CLAUDE_CODE_BACKEND", session_id=session_id,
            transport="DIRECT_CLI", upstream_provider="ANTHROPIC",
        )

    def test_lifecycle_events_and_same_task_rehydration(self):
        first = self._session()
        (self.repo / "progress.txt").write_text("step-one\n", encoding="utf-8")
        checkpoint = self.engine.checkpoint(
            "task-1", first.session_id, completed_steps=["STEP_ONE"],
            next_action="STEP_TWO", repository_root=self.repo,
        )
        self.engine.lose_session("task-1", first.session_id, "PROCESS_EXITED")
        second = self.engine.start_session(
            "task-1", "CLAUDE_CODE_BACKEND", session_id="session-2",
            transport="DIRECT_CLI", upstream_provider="ANTHROPIC",
        )
        restored = self.engine.rehydrate(
            "task-1", second.session_id, self.repo,
            authority_envelope_id=self.authority, authority_status="ACTIVE",
        )
        self.engine.resume("task-1", second.session_id)
        self.assertEqual(checkpoint.checkpoint_id, restored.checkpoint_id)
        self.assertNotEqual(first.session_id, second.session_id)
        status = self.engine.status("task-1")
        self.assertEqual("task-1", status["task_id"])
        self.assertEqual(["session-1", "session-2"], status["session_lineage"])
        self.assertEqual(1, status["restart_count"])

    def test_single_writer_and_stale_owner_rejected(self):
        self._session()
        with self.assertRaises(OwnershipError):
            self.engine.start_session("task-1", "CODEX_BACKEND", session_id="session-2")
        with self.assertRaises(OwnershipError):
            self.engine.checkpoint(
                "task-1", "stale-session", completed_steps=[], next_action="NONE",
                repository_root=self.repo,
            )

    def test_checkpoint_corruption_and_truncation_fail_closed(self):
        session = self._session()
        checkpoint = self.engine.checkpoint(
            "task-1", session.session_id, completed_steps=[], next_action="WORK",
            repository_root=self.repo,
        )
        path = self.store.checkpoints / f"{checkpoint.checkpoint_id}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["next_action"] = "MALICIOUS_REWRITE"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(IntegrityError):
            self.store.load_checkpoint(checkpoint.checkpoint_id)
        path.write_text('{"task_id":', encoding="utf-8")
        with self.assertRaises(IntegrityError):
            self.store.load_checkpoint(checkpoint.checkpoint_id)

    def test_atomic_write_failure_leaves_no_partial_record(self):
        task = self._task()
        path = self.store.tasks / f"{task.task_id}.json"
        before = path.read_bytes()
        original_replace = Path.replace

        def fail_replace(source, target):
            if str(source).endswith(".tmp"):
                raise OSError("injected crash before replace")
            return original_replace(source, target)

        task.state = "MUTATED"
        with patch.object(Path, "replace", autospec=True, side_effect=fail_replace):
            with self.assertRaises(OSError):
                self.store.save_task(task, expected_revision=task.revision)
        self.assertEqual(before, path.read_bytes())
        self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_concurrent_compare_and_set_has_one_winner(self):
        self._task()
        base = self.store.load_task("task-1")
        outcomes = []

        def write(state):
            candidate = self.store.load_task("task-1")
            candidate.revision = base.revision
            candidate.state = state
            try:
                self.store.save_task(candidate, expected_revision=base.revision)
                outcomes.append("PASS")
            except OwnershipError:
                outcomes.append("REJECTED")

        threads = [threading.Thread(target=write, args=(f"STATE_{index}",)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        self.assertCountEqual(["PASS", "REJECTED"], outcomes)

    def test_multi_process_compare_and_set_has_one_winner(self):
        task = self._task()
        context = multiprocessing.get_context("spawn")
        ready, results = context.Queue(), context.Queue()
        start = context.Event()
        processes = [
            context.Process(
                target=_multiprocess_cas_worker,
                args=(str(self.store.root), task.revision, f"PROCESS_{index}", ready, start, results),
            )
            for index in range(2)
        ]
        for process in processes:
            process.start()
        for _ in processes:
            ready.get(timeout=10)
        start.set()
        for process in processes:
            process.join(timeout=10)
            self.assertFalse(process.is_alive())
            self.assertEqual(0, process.exitcode)
        self.assertCountEqual(["PASS", "REJECTED"], [results.get(timeout=2) for _ in processes])

    def test_repository_change_requires_reconciliation(self):
        first = self._session()
        self.engine.checkpoint(
            "task-1", first.session_id, completed_steps=[], next_action="WORK",
            repository_root=self.repo,
        )
        self.engine.lose_session("task-1", first.session_id, "PROCESS_EXITED")
        (self.repo / "unexpected.txt").write_text("changed", encoding="utf-8")
        second = self.engine.start_session("task-1", "CLAUDE_CODE_BACKEND", session_id="session-2")
        with self.assertRaises(ReconciliationError):
            self.engine.rehydrate(
                "task-1", second.session_id, self.repo,
                authority_envelope_id=self.authority, authority_status="ACTIVE",
            )
        self.assertEqual("RECONCILIATION_REQUIRED", self.engine.status("task-1")["task_state"])

    def test_consumed_expired_and_revoked_authority_never_replay(self):
        for index, state in enumerate(("CONSUMED_CLOSED", "EXPIRED", "REVOKED")):
            task_id = f"authority-{index}"
            first = self._session(task_id, f"first-{index}")
            self.engine.checkpoint(
                task_id, first.session_id, completed_steps=[], next_action="WORK",
                repository_root=self.repo,
            )
            self.engine.lose_session(task_id, first.session_id, "PROCESS_EXITED")
            second = self.engine.start_session(task_id, "CLAUDE_CODE_BACKEND", session_id=f"second-{index}")
            with self.assertRaises(ReconciliationError):
                self.engine.rehydrate(
                    task_id, second.session_id, self.repo,
                    authority_envelope_id=self.authority, authority_status=state,
                )

    def test_host_verification_required_before_completion(self):
        session = self._session()
        with self.assertRaises(ContinuityError):
            self.engine.complete("task-1", session.session_id)
        self.engine.host_verified("task-1", session.session_id, True)
        task = self.engine.complete("task-1", session.session_id)
        self.assertEqual("TASK_COMPLETED", task.state)
        self.assertIsNone(task.active_session_id)
        self.assertIsNone(self.engine.status("task-1")["next_action"])

    def test_restart_reconstructs_engine_from_disk(self):
        first = self._session()
        self.engine.checkpoint(
            "task-1", first.session_id, completed_steps=["ONE"], next_action="TWO",
            repository_root=self.repo,
        )
        self.engine.lose_session("task-1", first.session_id, "PROCESS_EXITED")
        rebuilt = ContinuityEngine(TaskContinuityStore(self.root / "continuity"))
        second = rebuilt.start_session("task-1", "CLAUDE_CODE_BACKEND", session_id="fresh-process-session")
        restored = rebuilt.rehydrate(
            "task-1", second.session_id, self.repo,
            authority_envelope_id=self.authority, authority_status="ACTIVE",
        )
        self.assertEqual(["ONE"], restored.completed_steps)
        self.assertEqual("TWO", restored.next_action)

    def test_retry_limits_park_without_loop(self):
        first = self._session()
        self.engine.checkpoint(
            "task-1", first.session_id, completed_steps=[], next_action="WORK",
            repository_root=self.repo,
        )
        for index in range(2):
            active = self.engine.status("task-1")["active_session"]
            self.engine.lose_session("task-1", active, "PROCESS_EXITED")
            replacement = self.engine.start_session(
                "task-1", "CLAUDE_CODE_BACKEND", session_id=f"replacement-{index}"
            )
            self.engine.rehydrate(
                "task-1", replacement.session_id, self.repo,
                authority_envelope_id=self.authority, authority_status="ACTIVE",
            )
        self.engine.lose_session("task-1", "replacement-1", "PROCESS_EXITED")
        with self.assertRaises(ContinuityError):
            self.engine.start_session("task-1", "CLAUDE_CODE_BACKEND", session_id="loop")
        self.assertEqual("PARKED", self.engine.status("task-1")["task_state"])

    def test_blocker_policy(self):
        self.assertEqual("USAGE_QUOTA_LIMIT", classify_blocker("provider quota exhausted"))
        self.assertEqual("WAITING_RESOURCE", recovery_strategy("USAGE_QUOTA_LIMIT"))
        self.assertEqual("WAIT_AUTH", recovery_strategy("AUTH_REQUIRED"))
        self.assertEqual("WAIT_AUTHORITY", recovery_strategy("AUTHORITY_BLOCKED"))

    def test_same_parked_route_cannot_retry_without_material_change(self):
        session = self._session()
        self.engine.lose_session("task-1", session.session_id, "USAGE_QUOTA_LIMIT")
        with self.assertRaises(ContinuityError):
            self.engine.route("task-1", "CLAUDE_CODE_BACKEND")
        self.assertEqual("PARKED", self.engine.status("task-1")["task_state"])

    def test_checkpointed_preemption_requires_exact_material_wake(self):
        session = self._session()
        checkpoint = self.engine.checkpoint(
            "task-1", session.session_id, completed_steps=["UNIT_ONE"],
            next_action="UNIT_TWO", repository_root=self.repo,
        )
        parked = self.engine.preempt("task-1", session.session_id)
        self.assertEqual("PARKED", parked.state)
        self.assertEqual("REAL_WORK_PREEMPTION", parked.blocker_class)
        self.assertEqual("REAL_WORK_COMPLETED", parked.next_trigger)
        self.assertEqual(checkpoint.checkpoint_id, parked.last_checkpoint_id)
        with self.assertRaises(ReconciliationError):
            self.engine.material_wake("task-1", "UNRELATED_TRIGGER")
        ready = self.engine.material_wake("task-1", "REAL_WORK_COMPLETED")
        self.assertEqual("BACKEND_ROUTED", ready.state)
        self.assertIsNone(ready.blocker_class)
        replacement = self.engine.start_session(
            "task-1", "CLAUDE_CODE_BACKEND", session_id="after-real-work"
        )
        self.assertEqual("after-real-work", replacement.session_id)

    def test_transport_is_distinct_from_backend_and_upstream_provider(self):
        self._task()
        routed = self.engine.route(
            "task-1", "CLAUDE_CODE_BACKEND", transport="OMNIROUTE",
            upstream_provider="UNKNOWN",
        )
        self.assertEqual("CLAUDE_CODE_BACKEND", routed.backend)
        self.assertEqual("OMNIROUTE", routed.transport)
        self.assertEqual("UNKNOWN", routed.upstream_provider)

    def test_backend_substitution_is_bounded_and_preserves_task(self):
        first = self._session()
        self.engine.checkpoint(
            "task-1", first.session_id, completed_steps=[], next_action="WORK",
            repository_root=self.repo,
        )
        self.engine.lose_session("task-1", first.session_id, "PROCESS_EXITED")
        switched = self.engine.route("task-1", "CODEX_BACKEND")
        self.assertEqual("task-1", switched.task_id)
        self.assertEqual(1, switched.backend_switch_count)
        parked = self.engine.route("task-1", "HOST_LOCAL_EXECUTOR")
        self.assertEqual("PARKED", parked.state)
        self.assertEqual("BACKEND_SWITCH_LIMIT", parked.recovery_state)

    def test_rehydration_packet_is_durable_integrity_sealed_and_task_bound(self):
        session = self._session()
        self.engine.host_verified("task-1", session.session_id, True)
        self.engine.complete("task-1", session.session_id)
        fields = {
            "mission": "completed test mission", "last_verified_state": "PASS",
            "current_phase": "COMPLETED", "completed": ["WORK"], "current_step": "NONE",
            "current_blocker": None, "next_atomic_action": "NONE_FOR_THIS_TASK",
            "verified_results": {"tests": "PASS"}, "failed_attempts": [],
            "files_or_artifacts_used": ["fixture"], "important_hashes": {"fixture": "abc"},
            "authority": {"external": False}, "resource_blockers": [],
            "do_not_repeat": ["WORK"], "open_questions": [], "success_criteria": ["PASS"],
            "evidence": {"result": "PASS"}, "expected_final_state": "COMPLETE",
        }
        packet = self.engine.freeze_rehydration("task-1", **fields)
        duplicate = self.engine.freeze_rehydration("task-1", **fields)
        self.assertEqual(packet.packet_id, duplicate.packet_id)
        self.assertEqual(1, len(list(self.store.rehydration.glob("task-1.*.json"))))
        rebuilt = TaskContinuityStore(self.root / "continuity").latest_rehydration("task-1")
        self.assertEqual(packet.packet_id, rebuilt.packet_id)
        path = self.store.rehydration / f"task-1.{packet.packet_id}.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["mission"] = "tampered"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(IntegrityError):
            self.store.load_rehydration("task-1", packet.packet_id)

    def test_completed_task_cannot_be_rehydrated_as_active(self):
        session = self._session()
        self.engine.host_verified("task-1", session.session_id, True)
        self.engine.complete("task-1", session.session_id)
        with self.assertRaises(ReconciliationError):
            self.engine.freeze_rehydration(
                "task-1", mission="x", last_verified_state="PASS", current_phase="ACTIVE",
                completed=[], current_step="WORK", next_atomic_action="WORK", verified_results={},
                authority={}, do_not_repeat=[], success_criteria=[], evidence={}, expected_final_state="DONE",
            )


if __name__ == "__main__":
    unittest.main()
