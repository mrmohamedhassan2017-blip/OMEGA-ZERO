import tempfile
import unittest
from pathlib import Path

from omega.lzc14 import run_default_migration


class LZC14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.result = run_default_migration(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_hundred_eligible_runs_use_policy_default(self):
        self.assertEqual(len(self.result["default_selection_results"]), 2)
        self.assertEqual(self.result["default_selection_results"]["eligible_selected_lean"], 100)
        self.assertFalse(self.result["default_selection_results"]["manual_selector_required"])

    def test_ineligible_cases_never_select_lean(self):
        self.assertNotIn("LEAN_DEFAULT", self.result["ineligible_selection_results"].values())
        self.assertEqual(self.result["ineligible_selection_results"]["ambiguous_prior"], "PARK")

    def test_fallback_rollback_and_safety(self):
        self.assertTrue(self.result["fallback_drill_result"]["pass"])
        self.assertTrue(self.result["global_rollback_result"]["pass"])
        self.assertEqual(self.result["ownership_results"]["dual_authoritative"], 0)
        self.assertEqual(self.result["final_result"], "BOUNDED_LEAN_DEFAULT_STRONGLY_SUPPORTED")


if __name__ == "__main__":
    unittest.main()
