import json
import tempfile
import unittest
from pathlib import Path

from omega.lzc19c import freeze_health_model


class LZC19CTests(unittest.TestCase):
    def test_freezes_existing_episode_without_start(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); p = root / ".omega/zero"; p.mkdir(parents=True)
            (p / "lzc_v1_9b_result.json").write_text(json.dumps({"heartbeat_lock_identity_match_live_samples": True, "fresh_heartbeat_sample_count": 7, "heartbeat_advance_sample_count": 6, "post_stop_snapshot": {"lock_runtime_instance_id": None, "task": {"last_result": 0}}, "unsafe_process_terminations": 0, "authority_violations": 0}), encoding="utf-8")
            result = freeze_health_model(root)
            self.assertEqual(result["final_result"], "HARD_BLOCKER_HEALTH_MODEL_STRONGLY_SUPPORTED")
            self.assertFalse(result["runtime_started"])

    def test_unknowns_are_not_upgraded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / ".omega/zero").mkdir(parents=True)
            result = freeze_health_model(root)
            self.assertIn("repeatability", result["unknown_fields"])
            self.assertEqual(result["long_duration_temporal_evidence"], "NOT_YET_PROVEN")


if __name__ == "__main__": unittest.main()
