import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_ccs_cycle

class CCSTests(unittest.TestCase):
    def test_spec_frozen_and_all_required_cases_run(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_ccs_cycle(Path(t)); self.assertEqual(64,len(r["spec_hash"])); self.assertEqual(10,len(r["fixture_results"])); self.assertEqual("CCS-001",r["frozen_spec"]["experiment_id"])
    def test_strong_baseline_parity_kills_wedge(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_ccs_cycle(Path(t)); self.assertEqual("CCS_BASELINE_PARITY",r["state"]); self.assertTrue(all(x["delta"]=="NONE" for x in r["fixture_results"])); self.assertEqual("NONE",r["minimal_capability_form"])
    def test_external_authority_and_value_firewalls(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_ccs_cycle(Path(t)); self.assertEqual("CASE_DEPENDENT",r["authoritative_confirmation_required"]); self.assertEqual("L0",r["current_value_level"]); self.assertEqual(0,r["real_economic_value_kwd"])

if __name__=="__main__": unittest.main()
