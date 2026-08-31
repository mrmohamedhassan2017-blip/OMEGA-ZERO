import tempfile, unittest
from pathlib import Path
from omega.zero_truth import operate_urvk_cycle

class URVKTests(unittest.TestCase):
    def test_unified_cycle_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_urvk_cycle(Path(t)); self.assertEqual("NO_UNIQUE_WEDGE_FOUND",r["state"]); self.assertFalse(r["unique_wedge_found"]); self.assertEqual("L0",r["current_value_level"])
    def test_preserves_external_branches(self):
        with tempfile.TemporaryDirectory() as t:
            r=operate_urvk_cycle(Path(t)); self.assertIn("WAITING",r["v030_state"]); self.assertEqual("0_KWD", "0_KWD" if r["real_economic_value_kwd"]==0 else "bad")

if __name__=="__main__": unittest.main()
