import tempfile
import unittest
from pathlib import Path

from omega.provider_resilience import (backend_registry, checkpoint_task, classify_task,
                                       run_preb_simulation, schedule_quota_wait)


class ProviderResilienceTests(unittest.TestCase):
    def _task(self):
        return {"task_id": "t1", "branch": "b1", "frozen_inputs": ["x"], "repository_baseline": "h",
                "files_modified": [], "expected_outputs": ["y"], "tests_completed": [], "remaining_work": ["z"], "evidence_hashes": []}

    def test_registry_records_actual_backends_and_unknown_quota(self):
        registry = backend_registry(codex_state="QUOTA_EXHAUSTED", next_retry_at="2026-08-28T01:04:00+03:00")
        codex = registry["backends"][0]
        self.assertEqual("QUOTA_EXHAUSTED", codex["status"]); self.assertEqual("UNKNOWN", codex["quota_remaining"])
        self.assertEqual("AVAILABLE", registry["backends"][1]["status"])

    def test_classifier_keeps_deterministic_work_on_host(self):
        self.assertEqual("LOCAL_TEST", classify_task("run tests")); self.assertEqual("LOCAL_STATE_UPDATE", classify_task("verify hashes"))
        self.assertEqual("AI_CODE_EDIT_REQUIRED", classify_task("repair code", requires_reasoning=True, changes_code=True))

    def test_claude_resource_state_is_independent_and_does_not_replace_host(self):
        registry = backend_registry(codex_state="AVAILABLE", claude_state="WAITING_RESOURCE")
        by_id = {item["backend_id"]: item for item in registry["backends"]}
        self.assertEqual("AVAILABLE", by_id["CODEX_BACKEND"]["status"])
        self.assertEqual("AVAILABLE", by_id["HOST_LOCAL_EXECUTOR"]["status"])
        self.assertEqual("WAITING_RESOURCE", by_id["CLAUDE_CODE_BACKEND"]["status"])
        self.assertEqual("UNKNOWN", by_id["CLAUDE_CODE_BACKEND"]["quota_remaining"])

    def test_quota_exhaustion_checkpoints_without_retry_storm(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = schedule_quota_wait(Path(tmp), self._task(), "2026-08-28T01:04:00+03:00")
            self.assertEqual("WAITING_RESOURCE", result["checkpoint"]["status"]); self.assertFalse(result["wake"]["retry_storm"])
            self.assertEqual("2026-08-28T01:04:00+03:00", result["checkpoint"]["next_retry_at"])

    def test_host_continues_and_recovery_resumes_without_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_preb_simulation(Path(tmp))
            self.assertTrue(result["host_continuation"]["completed"]); self.assertEqual(1, result["recovery_probe"]["probes"])
            self.assertFalse(result["recovery_probe"]["duplicate_work"]); self.assertEqual("preb-integration-task", result["recovery_probe"]["resumed_task"])

    def test_checkpoint_requires_restart_safe_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): checkpoint_task(Path(tmp), {"task_id": "x"}, reason="x", backend_used="CODEX_BACKEND")


if __name__ == "__main__":
    unittest.main()
