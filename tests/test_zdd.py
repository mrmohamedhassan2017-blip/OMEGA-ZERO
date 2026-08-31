import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zdd_cycle

class ZDDTests(unittest.TestCase):
    def test_baseline_first_contract_and_shadow(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zdd_cycle(Path(t)); self.assertEqual(5,len(r["problem_classes"])); self.assertEqual("SIMULATED",r["contract"]["evidence_type"]); self.assertTrue(all(x["state"]=="SIMULATED_INTERNAL" for x in r["shadow_cases"]))
    def test_no_internal_promotion(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zdd_cycle(Path(t)); self.assertEqual("L0",r["current_value_level"]); self.assertFalse(r["external_experiment_justified"]); self.assertFalse(r["bottleneck_reduction"])
    def test_negative_and_alternative_recorded(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zdd_cycle(Path(t)); self.assertTrue(all("best_existing_alternative" in x for x in r["problem_classes"])); self.assertIn("baseline",r["red_objection"].lower())
