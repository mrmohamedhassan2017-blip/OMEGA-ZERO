import tempfile
import unittest
from pathlib import Path

from omega.zdoa import run_zdoa


class ZDOATests(unittest.TestCase):
    def test_spec_is_frozen_and_all_runs_execute(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_zdoa(Path(folder))
        self.assertEqual(64,len(result["spec_hash"]))
        self.assertEqual(90,result["run_results"]["runs"])
        self.assertEqual(6,len(result["test_regimes"]))

    def test_information_authority_and_outcomes_are_at_parity(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_zdoa(Path(folder))
        self.assertEqual("VERIFIED_BY_SHARED_WORLD_OBJECT",result["information_parity"])
        self.assertEqual(0,result["authority_violations"])
        self.assertTrue(result["baseline_comparison"]["utility_equal"])
        self.assertTrue(result["baseline_comparison"]["regret_equal"])

    def test_complexity_tax_prevents_false_advantage(self):
        with tempfile.TemporaryDirectory() as folder:
            result=run_zdoa(Path(folder))
        self.assertEqual("ZERO_BASELINE_PARITY",result["final_comparative_result"])
        self.assertEqual("HIGH",result["complexity_tax"])
        self.assertEqual("YES",result["baseline_parity"])
        self.assertIsNone(result["demonstrated_advantage_profile"])
        self.assertEqual("L0",result["repository_truth"]["current_evidence_level"])
        self.assertEqual(0,result["repository_truth"]["real_economic_value_kwd"])


if __name__ == "__main__":
    unittest.main()
