import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_zopd_cycle


class ZOPDTests(unittest.TestCase):
    def test_discovery_has_diverse_observed_events_and_funnel(self):
        with tempfile.TemporaryDirectory() as folder:
            result = operate_zopd_cycle(Path(folder))
        self.assertGreaterEqual(len(result["public_problem_evidence"]), 20)
        self.assertGreaterEqual(len({e["domain"] for e in result["public_problem_evidence"]}), 8)
        self.assertEqual(10, len(result["top_10"]))
        self.assertEqual(5, len(result["top_5"]))
        self.assertEqual(3, len(result["top_3"]))
        self.assertTrue(all(e["epistemic"]["demand"] == "UNKNOWN" for e in result["public_problem_evidence"]))

    def test_strong_baselines_prevent_false_winner(self):
        with tempfile.TemporaryDirectory() as folder:
            result = operate_zopd_cycle(Path(folder))
        self.assertEqual("DISCOVERY_COMPLETE_NO_WINNER", result["state"])
        self.assertIsNone(result["winning_research_direction"])
        self.assertIsNone(result["winning_value_primitive"])
        self.assertEqual("NONE", result["value_exclusivity"])

    def test_value_and_authority_firewalls_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            result = operate_zopd_cycle(Path(folder))
        self.assertEqual("L0", result["repository_truth"]["current_value_level"])
        self.assertEqual(0, result["repository_truth"]["real_economic_value_kwd"])
        self.assertFalse(result["global_wait_required"])
        self.assertEqual("UNKNOWN", result["owner_controlled_test_available"])


if __name__ == "__main__":
    unittest.main()
