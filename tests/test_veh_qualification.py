import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_veh_qualification_cycle


class VEHQualificationTests(unittest.TestCase):
    def test_unproven_assets_do_not_become_fake_options(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_qualification_cycle(Path(folder))
        self.assertEqual("VEH_NO_OPTION_AVAILABLE",result["state"])
        self.assertIsNone(result["qualified_option"])
        self.assertTrue(all(value != "QUALIFIED" for value in result["qualification_results"].values()))

    def test_privacy_and_experiment_integrity_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_qualification_cycle(Path(folder))
        self.assertTrue(result["privacy_check"]["passed"])
        self.assertFalse(result["privacy_check"]["stored_sensitive_data"])
        self.assertTrue(result["experiment_integrity_check"]["baseline_first_preserved"])
        self.assertFalse(result["experiment_integrity_check"]["zero_analysis_performed"])
        self.assertFalse(result["experiment_integrity_check"]["external_action"])

    def test_negative_result_preserves_value_and_authority_firewalls(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_veh_qualification_cycle(Path(folder))
        self.assertEqual("L0",result["repository_truth"]["current_value_level"])
        self.assertEqual(0,result["repository_truth"]["real_economic_value_kwd"])
        self.assertEqual("UNKNOWN",result["authority_verified"])
        self.assertEqual("NO",result["baseline_identified"])
        self.assertTrue(result["global_wait_required"])


if __name__ == "__main__":
    unittest.main()
