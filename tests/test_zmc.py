import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zmc_cycle

class ZMCTests(unittest.TestCase):
    def test_cycle_separates_problem_from_motivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=operate_zmc_cycle(Path(tmp)); self.assertEqual(5,len(r["structural_opportunities"])); self.assertEqual("EXPECTED_UTILITY",r["dominant_motivation_child"]["id"]); self.assertEqual("L0",r["current_value_level"])
    def test_shadow_consumer_cannot_promote_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=operate_zmc_cycle(Path(tmp)); self.assertTrue(all(x["state"]=="SIMULATED_OWNER_CONTROLLED" for x in r["shadow_result"])); self.assertEqual("UNPROVEN",r["h_endogenous_motivation"]["status"])
    def test_no_external_action_and_zero_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=operate_zmc_cycle(Path(tmp)); self.assertFalse(r["atomic_experiment"]["external_action"]); self.assertIsNone(r["authorization_required"]); self.assertEqual(0,r["real_economic_value_kwd"])

if __name__=="__main__": unittest.main()
