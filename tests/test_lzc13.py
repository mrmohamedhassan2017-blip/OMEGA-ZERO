import tempfile
import unittest
from pathlib import Path

from omega.lzc13 import EXPECTED_CORE_HASH, run_second_workflow


class LZC13Tests(unittest.TestCase):
    def run_result(self):
        with tempfile.TemporaryDirectory() as folder:
            return run_second_workflow(Path(folder))

    def test_fifty_second_domain_runs_and_unchanged_api(self):
        result = self.run_result()
        self.assertEqual(len(result["controlled_run_results"]), 50)
        self.assertEqual(result["core_api_hash_check"]["actual"], EXPECTED_CORE_HASH)
        self.assertEqual(result["core_api_stability_result"]["api_change_requests"], 0)

    def test_file_safety_and_one_path(self):
        result = self.run_result()
        self.assertTrue(result["normal_results"]["all_verified"])
        self.assertEqual(result["partial_write_results"]["corrupted_commits"], 0)
        self.assertTrue(result["one_path_result"]["pass"])
        self.assertEqual(result["authority_results"]["violations"], 0)

    def test_cross_domain_gate_and_rollback(self):
        result = self.run_result()
        self.assertEqual(result["final_result"], "SECOND_WORKFLOW_CONTROLLED_USE_STRONGLY_SUPPORTED")
        self.assertEqual(result["multi_workflow_gate"], "SUPPORTED")
        self.assertTrue(result["rollback_result"]["pass"])
        self.assertEqual(result["production_status"].split(";")[0], "LEGACY_DEFAULT")


if __name__ == "__main__":
    unittest.main()
