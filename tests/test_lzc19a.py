import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from omega.lzc19a import collect_diagnostic_sample, run_heartbeat_diagnosis


class LZC19ATests(unittest.TestCase):
    def _state(self, root: Path) -> None:
        runtime = root / ".omega" / "runtime"; runtime.mkdir(parents=True)
        heartbeat = {"status": "RUNNING", "pid": 999999, "process_created_at": "2026-08-28T19:46:27+03:00",
                     "runtime_instance_id": "one", "last_heartbeat": "2026-08-28T19:46:53+03:00"}
        (runtime / "heartbeat.json").write_text(json.dumps(heartbeat), encoding="utf-8")
        (runtime / "supervisor.lock").write_text(json.dumps({"pid": 999999, "process_created_at": heartbeat["process_created_at"],
                                                               "runtime_instance_id": "one"}), encoding="utf-8")

    def test_stopped_pid_is_residual_not_valid_identity(self):
        with tempfile.TemporaryDirectory() as folder, patch("omega.lzc19a.Supervisor._pid_alive", return_value=False):
            root = Path(folder); self._state(root)
            sample = collect_diagnostic_sample(root, observed_at=datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc))
        self.assertFalse(sample["process_alive"]); self.assertFalse(sample["identity_valid"])
        self.assertTrue(sample["cross_file_identity_consistent"]); self.assertFalse(sample["heartbeat_fresh"])

    def test_stopped_task_classifies_expected_stale_without_repair(self):
        sample = {"heartbeat_file_present": True, "heartbeat_logical_timestamp": "old", "heartbeat_file_mtime_ns": 1,
                  "heartbeat_age_seconds": 500, "heartbeat_fresh": False, "pid": 99, "process_alive": False,
                  "identity_valid": False, "cross_file_identity_consistent": True, "runtime_instance_id": "one"}
        ticks = iter([0.0, 0.0, .05, .06])
        with tempfile.TemporaryDirectory() as folder:
            result = run_heartbeat_diagnosis(Path(folder), .05, .05, clock=lambda: next(ticks), sleeper=lambda _: None,
                                             sample_fn=lambda root: dict(sample), scheduled_task_state=lambda: "READY")
        self.assertEqual(result["final_result"], "HEARTBEAT_STALE_EXPECTED_SUPERVISOR_NOT_RUNNING")
        self.assertFalse(result["repair_applied"]); self.assertEqual(result["heartbeat_writer_count"], 0)

    def test_no_false_progression_from_constant_timestamp_or_mtime(self):
        sample = {"heartbeat_file_present": True, "heartbeat_logical_timestamp": "same", "heartbeat_file_mtime_ns": 7,
                  "heartbeat_age_seconds": 500, "heartbeat_fresh": False, "pid": 99, "process_alive": False,
                  "identity_valid": False, "cross_file_identity_consistent": True, "runtime_instance_id": "one"}
        ticks = iter([0.0, 0.0, .05, .1, .11])
        with tempfile.TemporaryDirectory() as folder:
            result = run_heartbeat_diagnosis(Path(folder), .1, .05, clock=lambda: next(ticks), sleeper=lambda _: None,
                                             sample_fn=lambda root: dict(sample), scheduled_task_state=lambda: "READY")
        self.assertEqual(result["short_diagnostic_sample_count"], 3)
        self.assertEqual(result["advancing_heartbeat_samples"], 0); self.assertEqual(result["advancing_mtime_samples"], 0)


if __name__ == "__main__":
    unittest.main()
