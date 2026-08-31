import tempfile, unittest
from pathlib import Path
from omega.lzc11 import run_campaign
class LZC11Tests(unittest.TestCase):
    def test_campaign_completes_without_drift(self):
        with tempfile.TemporaryDirectory() as d: r = run_campaign(Path(d))
        self.assertEqual(len(r["run_results"]), 100); self.assertEqual(r["final_result"], "LONG_RUN_SHADOW_STRONGLY_SUPPORTED")
        self.assertFalse(r["cross_run_drift_result"]["drift"])
    def test_safety_and_stress_quotas(self):
        with tempfile.TemporaryDirectory() as d: r = run_campaign(Path(d))
        self.assertEqual(r["restart_results"]["passed"], 10); self.assertEqual(r["timeout_results"]["passed"], 10); self.assertEqual(r["resume_results"]["passed"], 20)
        self.assertEqual(r["safety_results"]["authority_violations"], 0)
    def test_api_is_frozen(self):
        with tempfile.TemporaryDirectory() as d: r = run_campaign(Path(d))
        self.assertTrue(r["core_api_hash_check"]["valid"]); self.assertEqual(r["api_stability_result"], "PASS")
