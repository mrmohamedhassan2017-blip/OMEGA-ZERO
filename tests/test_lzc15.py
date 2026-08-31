import tempfile
import unittest
from pathlib import Path

from omega.lzc15 import run_extended_stability


class LZC15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.result = run_extended_stability(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_campaign_and_stress_quotas(self):
        self.assertEqual(len(self.result["run_results"]), 500)
        self.assertEqual(self.result["restart_results"]["passed"], 25)
        self.assertEqual(self.result["fallback_results"]["passed"], 10)
        self.assertEqual(self.result["global_rollback_results"]["passed"], 5)

    def test_resource_state_and_safety_are_clean(self):
        self.assertEqual(self.result["sqlite_resource_results"]["resource_leaks"], 0)
        self.assertTrue(self.result["sqlite_resource_results"]["temp_directory_released"])
        self.assertEqual(self.result["state_isolation_results"]["state_leaks"], 0)
        self.assertTrue(all(value == 0 for value in self.result["safety_results"].values()))

    def test_api_legacy_and_result(self):
        self.assertEqual(self.result["api_stability_results"]["core_api_change_requests"], 0)
        self.assertEqual(self.result["legacy_health_results"], "PASS")
        self.assertEqual(self.result["final_result"], "EXTENDED_DEFAULT_STABILITY_STRONGLY_SUPPORTED")


if __name__ == "__main__":
    unittest.main()
