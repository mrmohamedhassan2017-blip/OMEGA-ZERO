import tempfile
import unittest
from pathlib import Path

from omega.lzc17 import run_time_canary


class LZC17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.result = run_time_canary(Path(cls.temp.name), .15, evidence_mode="DETERMINISTIC_TEST_CLOCK")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_elapsed_harness_parks_wakes_and_revalidates(self):
        self.assertGreaterEqual(self.result["actual_duration_seconds"], .14)
        self.assertEqual(self.result["park_wake_results"]["lost_wakes"], 0)
        self.assertEqual(self.result["authority_revalidation_results"]["stale_acceptances"], 0)

    def test_temporal_and_cross_cohort_safety(self):
        self.assertTrue(all(value == 0 for value in self.result["cross_cohort_results"].values()))
        self.assertTrue(all(value == 0 for value in self.result["safety_results"].values()))
        self.assertEqual(self.result["architectural_boundary_result"], "PASS")

    def test_core_and_production_boundaries(self):
        self.assertEqual(self.result["api_stability_results"]["core_api_change_requests"], 0)
        self.assertEqual(self.result["final_result"], "TIME_BASED_MULTI_COHORT_STRONGLY_SUPPORTED")
        self.assertTrue(self.result["production_status"].startswith("GLOBAL_DEFAULT_LEGACY"))


if __name__ == "__main__":
    unittest.main()
