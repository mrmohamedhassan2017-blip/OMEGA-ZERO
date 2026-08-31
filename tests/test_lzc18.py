import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from omega.lzc18 import project_heartbeat, run_supervisor_shadow, shadow_decision


class LZC18Tests(unittest.TestCase):
    def test_shadow_has_zero_process_or_supervisor_side_effects(self):
        with tempfile.TemporaryDirectory() as folder, patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
            result = run_supervisor_shadow(Path(folder))
        run.assert_not_called(); popen.assert_not_called()
        self.assertTrue(all(value == 0 for value in result["side_effect_audit"].values()))
        self.assertEqual(result["responsibility_collisions"], 0)

    def test_stale_missing_and_identity_mismatch_fail_closed(self):
        observed = datetime(2026, 8, 28, 8, tzinfo=timezone.utc)
        stale = project_heartbeat({"status": "RUNNING", "last_heartbeat": "2026-08-28T07:00:00+00:00", "runtime_instance_id": "one"}, expected_runtime_id="one", observed_at=observed)
        mismatch = project_heartbeat({"status": "RUNNING", "last_heartbeat": "2026-08-28T07:59:59+00:00", "runtime_instance_id": "old"}, expected_runtime_id="new", observed_at=observed)
        self.assertEqual(shadow_decision(stale)["decision"], "WOULD_REJECT_STALE_OWNER")
        self.assertEqual(shadow_decision(mismatch)["decision"], "WOULD_REJECT_STALE_OWNER")
        self.assertEqual(shadow_decision(project_heartbeat({}, expected_runtime_id="new", observed_at=observed))["decision"], "UNKNOWN_FAIL_CLOSED")

    def test_parity_replay_and_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_supervisor_shadow(Path(folder))
        self.assertTrue(all(record["parity"] for record in result["lifecycle_case_results"]))
        self.assertEqual(result["replay_result"], "PASS")
        self.assertEqual(result["final_result"], "SUPERVISOR_SHADOW_STRONGLY_SUPPORTED")
        self.assertIn("LEAN_AUTHORITY_NONE", result["production_status"])


if __name__ == "__main__":
    unittest.main()
