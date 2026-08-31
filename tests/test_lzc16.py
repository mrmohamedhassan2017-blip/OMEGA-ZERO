import tempfile
import unittest
from pathlib import Path

from omega.lzc16 import run_multi_default


class LZC16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.result = run_multi_default(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_two_cohorts_and_five_hundred_runs(self):
        self.assertEqual(len(self.result["default_cohorts"]), 2)
        self.assertEqual(self.result["cohort_a_results"]["runs"], 250)
        self.assertEqual(self.result["cohort_b_results"]["runs"], 250)
        self.assertEqual(self.result["interleaving_results"]["pairs"], 250)

    def test_isolation_resources_and_fallbacks(self):
        self.assertTrue(self.result["cross_cohort_leak_results"]["all_zero"])
        self.assertEqual(self.result["process_resource_results"]["orphan_processes"], 0)
        self.assertEqual(self.result["sqlite_resource_results"]["leaks"], 0)
        self.assertEqual(self.result["fallback_results"], {"cohort_a": 5, "cohort_b": 5})
        self.assertEqual(self.result["global_rollback_results"]["passed"], 3)

    def test_core_and_production_boundaries(self):
        self.assertEqual(self.result["core_api_stability"]["core_api_change_requests"], 0)
        self.assertEqual(self.result["domain_leak_result"], "NONE")
        self.assertEqual(self.result["final_result"], "MULTI_COHORT_DEFAULT_STRONGLY_SUPPORTED")
        self.assertTrue(self.result["production_status"].startswith("GLOBAL_DEFAULT_LEGACY"))


if __name__ == "__main__":
    unittest.main()
