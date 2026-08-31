import tempfile, unittest
from pathlib import Path
from omega.lzc12 import run_controlled
class LZC12Tests(unittest.TestCase):
    def test_fifty_bounded_controlled_runs(self):
        with tempfile.TemporaryDirectory() as d: r = run_controlled(Path(d))
        self.assertEqual(len(r["controlled_run_results"]), 50); self.assertEqual(r["final_result"], "LEAN_CONTROLLED_USE_STRONGLY_SUPPORTED")
    def test_safety_and_rollback(self):
        with tempfile.TemporaryDirectory() as d: r = run_controlled(Path(d))
        self.assertEqual(r["authority_results"]["violations"], 0); self.assertTrue(r["dual_path_results"]["one_authoritative_path"]); self.assertTrue(r["rollback_drill_result"]["pass"])
    def test_legacy_remains_default(self):
        with tempfile.TemporaryDirectory() as d: r = run_controlled(Path(d))
        self.assertEqual(r["selector_spec"]["default"], "LEGACY"); self.assertEqual(r["production_status"].split(";")[0], "LEGACY_DEFAULT")
