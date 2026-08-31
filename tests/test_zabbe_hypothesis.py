import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zabbe_hypothesis_cycle

class ZABBEHypothesisTests(unittest.TestCase):
    def test_contract_is_bound_and_active_testing_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zabbe_hypothesis_cycle(Path(t)); self.assertTrue(r["authority_revalidated"]); self.assertFalse(r["active_security_testing_authorized"]); self.assertEqual(r["program_scope_hash"],r["contract"]["program_scope_hash"])
    def test_self_controlled_low_request_contract(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zabbe_hypothesis_cycle(Path(t)); c=r["contract"]; self.assertEqual("SELF_CONTROLLED_SYNTHETIC_DATA_ONLY",c["data_boundary"]); self.assertLessEqual(c["request_budget_proposed"],6); self.assertEqual(1,c["concurrency_proposed"])
    def test_shadow_is_internal_only(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zabbe_hypothesis_cycle(Path(t)); self.assertTrue(all(x["classification"]=="SIMULATED_INTERNAL" for x in r["shadow_walkthrough"])); self.assertEqual("L0",r["current_value_level"])

if __name__=="__main__": unittest.main()
