import tempfile
import unittest
from pathlib import Path

from omega.zero_truth import operate_zmc_convergence_cycle


class ZMCConvergenceTests(unittest.TestCase):
    def test_registers_unproven_hypothesis_and_exactly_one_project(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zmc_convergence_cycle(Path(folder))
        self.assertEqual("UNPROVEN",result["h_veh_001"]["status"])
        self.assertEqual("VEH-001",result["master_active_project"]["project_id"])
        self.assertEqual("D_ACQUIRE_LEGITIMATE_OWNER_CONTROLLED_TEST_SURFACE",result["master_convergence_decision"])

    def test_baselines_and_authority_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zmc_convergence_cycle(Path(folder))
        self.assertEqual(5,len(result["top_5_options"]))
        self.assertTrue(all(option["baseline"] for option in result["top_5_options"]))
        self.assertTrue(all(option["right_evidence"] and option["authority_access"] for option in result["top_5_options"]))
        self.assertEqual("WEAK",result["execution_gap_advantage"])

    def test_no_synthetic_value_or_unauthorized_action(self):
        with tempfile.TemporaryDirectory() as folder:
            result=operate_zmc_convergence_cycle(Path(folder))
        self.assertEqual("L0",result["repository_truth"]["current_evidence_level"])
        self.assertEqual(0,result["repository_truth"]["real_economic_value_kwd"])
        self.assertEqual("YES",result["owner_controlled_test_surface_required"])
        self.assertTrue(result["global_wait_required"])
        self.assertIn("no credentials",result["master_active_project"]["max_scope"])


if __name__ == "__main__":
    unittest.main()
