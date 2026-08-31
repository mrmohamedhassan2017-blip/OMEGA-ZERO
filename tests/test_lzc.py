import tempfile, unittest
from pathlib import Path
from omega.lzc import run_lzc
class LZCTests(unittest.TestCase):
    def test_shadow_is_supported_without_switch(self):
        with tempfile.TemporaryDirectory() as d: r = run_lzc(Path(d))
        self.assertEqual(r["final_decision"], "LEAN_ZERO_CORE_SHADOW_SUPPORTED"); self.assertEqual(r["production_status"].split(";")[0], "LEGACY_DEFAULT")
    def test_api_stability_and_no_leak(self):
        with tempfile.TemporaryDirectory() as d: r = run_lzc(Path(d))
        self.assertEqual(r["api_stability_result"], "PASS"); self.assertEqual(r["domain_leak_result"], "NONE")
    def test_all_cases_have_parity(self):
        with tempfile.TemporaryDirectory() as d: r = run_lzc(Path(d))
        self.assertTrue(all(v["parity"] for v in r["shadow_case_results"].values()))
