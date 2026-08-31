import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_veh_subscription_phase1


class VEHSubscriptionTests(unittest.TestCase):
    def test_owner_declarations_do_not_freeze_incomplete_option(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_subscription_phase1(Path(folder))
        self.assertEqual("OWNER_DECLARED",result["owner_declared_facts"]["evidence_class"])
        self.assertEqual(3,len(result["remaining_minimum_inputs"]))
        self.assertEqual("NOT_FROZEN_INCOMPLETE",result["raw_option_freeze_status"])
        self.assertIsNone(result["raw_option_hash"])

    def test_zero_and_external_actions_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_subscription_phase1(Path(folder))
        self.assertFalse(result["zero_analysis_allowed"])
        self.assertEqual("NOT_FROZEN",result["baseline_freeze_status"])
        self.assertEqual("EXTERNAL_ACTION_NOT_AUTHORIZED",result["action_authorization_status"])
        self.assertEqual("L0",result["repository_truth"]["current_value_level"])
        self.assertEqual(0,result["repository_truth"]["real_economic_value_kwd"])


if __name__ == "__main__":
    unittest.main()
