import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zavae_cycle

class ZAVAETests(unittest.TestCase):
    def test_lanes_remain_separate_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zavae_cycle(Path(t)); self.assertEqual("NO_ACTIONABLE_DORMANT_ASSETS",r["zdam"]["state"]); self.assertEqual("PROGRAM_READY_FOR_HYPOTHESIS_DESIGN",r["zabbe"]["state"]); self.assertFalse(r["zabbe"]["active_security_testing_authorized"]); self.assertTrue(r["zabbe"]["authorization_contract_complete"])
    def test_no_value_promotion(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zavae_cycle(Path(t)); self.assertEqual("L0",r["current_value_level"]); self.assertEqual(0,r["real_economic_value_kwd"]); self.assertEqual("DAM2",r["zdam"]["dam_level"])

if __name__=="__main__": unittest.main()
