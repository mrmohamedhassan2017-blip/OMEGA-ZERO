import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_zad_cycle


class ZADTests(unittest.TestCase):
    def test_all_killed_wedges_have_strong_baseline_explanations(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zad_cycle(Path(folder))
        self.assertGreaterEqual(len(result["past_baseline_failures"]),6)
        self.assertTrue(all(x["winning_baseline"] and x["zero_failed_to_add"] for x in result["past_baseline_failures"]))

    def test_capabilities_are_not_promoted_to_advantage(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zad_cycle(Path(folder))
        self.assertEqual("NO_DEMONSTRATED_COMPARATIVE_ADVANTAGE",result["state"])
        self.assertEqual("NONE_DEMONSTRATED",result["zero_primary_advantage"])
        self.assertEqual("F_ZERO_HAS_NO_DEMONSTRATED_COMPARATIVE_ADVANTAGE_YET",result["master_decision"])
        self.assertEqual("DESIGNED_NOT_RUN",result["cheapest_advantage_falsification_experiment"]["status"])

    def test_value_firewall_and_killed_wedges_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zad_cycle(Path(folder))
        self.assertTrue(result["repository_truth"]["killed_wedges_preserved"])
        self.assertEqual("L0",result["repository_truth"]["current_evidence_level"])
        self.assertEqual(0,result["repository_truth"]["real_economic_value_kwd"])
        self.assertEqual("UNKNOWN",result["economic_engine_shape"])
        self.assertTrue(result["global_wait_required"])


if __name__ == "__main__":
    unittest.main()
