import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zabbe_cycle

class ZABBETests(unittest.TestCase):
    def test_scope_uncertainty_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zabbe_cycle(Path(t)); self.assertEqual("AUTHORIZATION_DENIED_OR_UNCLEAR",r["state"]); self.assertEqual(0,r["request_budget_used"]); self.assertEqual("B0",r["bounty_evidence_level"])
    def test_no_active_testing_or_value(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zabbe_cycle(Path(t)); self.assertIsNone(r["program_winner"]); self.assertFalse(r["report_ready"]); self.assertEqual(0,r["real_economic_value_kwd"])

if __name__=="__main__": unittest.main()
