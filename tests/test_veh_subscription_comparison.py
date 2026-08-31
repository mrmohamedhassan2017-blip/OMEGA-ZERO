import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_veh_subscription_comparison


class VEHSubscriptionComparisonTests(unittest.TestCase):
    def test_raw_and_baseline_are_frozen_before_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_subscription_comparison(Path(folder))
        self.assertTrue(result["raw_option_frozen"])
        self.assertTrue(result["baseline_frozen"])
        self.assertEqual(64,len(result["raw_option_hash"]))
        self.assertEqual(64,len(result["baseline_hash"]))
        self.assertEqual(result["baseline_hash"],result["zero_result"]["baseline_hash"])
        self.assertEqual("CLEAN_BASELINE_HASHED_BEFORE_ZERO",result["experiment_contamination_status"])

    def test_uncertain_usage_produces_baseline_parity_not_cancellation(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_subscription_comparison(Path(folder))
        self.assertEqual("REVIEW",result["baseline_result"]["baseline_decision"])
        self.assertEqual("INSUFFICIENT_EVIDENCE",result["zero_result"]["decision"])
        self.assertEqual("BASELINE_PARITY",result["comparison"]["classification"])
        self.assertFalse(result["comparison"]["differentiated_action"])
        self.assertEqual("NONE",result["veh_value_exclusivity"])

    def test_no_action_or_value_promotion(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_subscription_comparison(Path(folder))
        self.assertEqual("EXTERNAL_ACTION_NOT_AUTHORIZED",result["action_authorization_status"])
        self.assertEqual(0,result["verified_realized_value"])
        self.assertEqual("L0",result["repository_truth"]["current_value_level"])
        self.assertEqual("KILLED_BASELINE_PARITY",result["veh_001_state"])


if __name__ == "__main__":
    unittest.main()
