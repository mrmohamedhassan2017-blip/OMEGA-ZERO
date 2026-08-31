import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from omega.lzc19 import _observer_lock, collect_sample, observation_spec, run_long_supervisor_shadow


class LZC19Tests(unittest.TestCase):
    def _runtime(self, root: Path) -> None:
        runtime = root / ".omega" / "runtime"
        runtime.mkdir(parents=True)
        heartbeat = {
            "status": "RUNNING", "pid": 42, "process_created_at": "2026-08-28T00:00:00+00:00",
            "runtime_instance_id": "runtime-one", "last_heartbeat": "2026-08-28T00:00:00+00:00",
            "current_task": "bounded task", "last_test_result": "PASS", "retry_count": 0,
            "blocker": None, "approval_required": False,
        }
        (runtime / "heartbeat.json").write_text(json.dumps(heartbeat), encoding="utf-8")
        (runtime / "supervisor.lock").write_text(json.dumps({
            "pid": 42, "process_created_at": heartbeat["process_created_at"],
            "runtime_instance_id": "runtime-one",
        }), encoding="utf-8")

    def test_sample_is_read_only_and_identity_aware(self):
        with tempfile.TemporaryDirectory() as folder, patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
            root = Path(folder); self._runtime(root)
            sample = collect_sample(root, now=datetime(2026, 8, 28, 0, 0, 20, tzinfo=timezone.utc))
        run.assert_not_called(); popen.assert_not_called()
        self.assertTrue(sample["valid"])
        self.assertTrue(sample["worker_identity_consistent"])
        self.assertEqual(sample["lean_shadow_decision"], "WOULD_RUN")

    def test_stale_heartbeat_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self._runtime(root)
            sample = collect_sample(root, now=datetime(2026, 8, 28, 0, 10, tzinfo=timezone.utc))
        self.assertFalse(sample["heartbeat_fresh"])
        self.assertEqual(sample["lean_shadow_decision"], "WOULD_REJECT_STALE_OWNER")
        self.assertEqual(sample["authoritative_state"], "WOULD_REJECT_STALE_OWNER")
        self.assertTrue(sample["parity"])

    def test_cross_file_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self._runtime(root)
            lock = root / ".omega" / "runtime" / "supervisor.lock"
            value = json.loads(lock.read_text(encoding="utf-8")); value["pid"] = 9001
            lock.write_text(json.dumps(value), encoding="utf-8")
            sample = collect_sample(root, now=datetime(2026, 8, 28, 0, 0, 20, tzinfo=timezone.utc))
        self.assertFalse(sample["worker_identity_consistent"])
        self.assertEqual(sample["lean_shadow_decision"], "WOULD_REJECT_STALE_OWNER")

    def test_age_change_is_not_counted_as_source_heartbeat_update(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self._runtime(root)
            first = collect_sample(root, now=datetime(2026, 8, 28, 0, 0, 20, tzinfo=timezone.utc))
            second = collect_sample(root, now=datetime(2026, 8, 28, 0, 0, 40, tzinfo=timezone.utc))
        self.assertNotEqual(first["input_state_hash"], second["input_state_hash"])
        self.assertEqual(first["heartbeat_timestamp_hash"], second["heartbeat_timestamp_hash"])

    def test_short_observation_cannot_claim_long_duration(self):
        ticks = iter([0.0, 0.0, 0.0, 0.06, 0.06, 0.06])
        with tempfile.TemporaryDirectory() as folder, patch("omega.lzc19.collect_sample") as collect:
            root = Path(folder)
            collect.return_value = {"valid": True, "runtime_instance_id_hash": "one", "lifecycle_state": "RUNNING",
                                    "heartbeat_fresh": True, "worker_identity_consistent": True,
                                    "verification_state": "PASS", "lean_shadow_decision": "WOULD_RUN",
                                    "authoritative_state": "WOULD_RUN", "input_state_hash": "x", "parity": True,
                                    "mismatch_class": None}
            result = run_long_supervisor_shadow(root, .05, .05, clock=lambda: next(ticks), sleeper=lambda _: None)
        self.assertEqual(result["long_duration_evidence_state"], "NOT_YET_PROVEN")
        self.assertNotEqual(result["final_result"], "LONG_SUPERVISOR_SHADOW_STRONGLY_SUPPORTED")
        self.assertEqual(result["shadow_side_effects"], 0)

    def test_spec_is_bounded_and_frozen(self):
        spec = observation_spec(3600, 30)
        self.assertEqual(spec["expected_sample_count"], 121)
        self.assertEqual(spec["authority"], "READ_ONLY_NON_AUTHORITATIVE")
        self.assertFalse(spec["storage_limits"]["raw_event_content_persisted"])

    def test_duplicate_observer_writer_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "observer.lock"
            with _observer_lock(lock):
                with self.assertRaisesRegex(RuntimeError, "already owns"):
                    with _observer_lock(lock):
                        pass


if __name__ == "__main__":
    unittest.main()
