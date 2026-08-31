import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_zmim_cycle

class ZMIMTests(unittest.TestCase):
    def test_public_pain_does_not_promote_demand(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zmim_cycle(Path(t)); self.assertEqual("L0",r["current_value_level"]); self.assertEqual("UNPROVEN",r["hypothesis_updates"]["H-MOTIVATION-01"]); self.assertEqual(0,r["real_economic_value_kwd"])
    def test_current_offer_can_be_weakened(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_zmim_cycle(Path(t)); self.assertEqual("WEAKENED",r["hypothesis_updates"]["H-AUDIT-WEDGE-01"]); self.assertTrue(all(x["decision_before"]==x["decision_after"] for x in r["marginal_utility_findings"]))

if __name__=="__main__": unittest.main()
