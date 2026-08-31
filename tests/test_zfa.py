import tempfile
import unittest
from pathlib import Path

from omega.zfa import run_zfa


class ZFATests(unittest.TestCase):
    def test_legacy_and_zfbr_backup_results_have_parity(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zfa(Path(folder))
        self.assertEqual("SQLite database backup to a local file", result["selected_workflow"])
        self.assertTrue(result["normal_parity_result"]["final_result"])
        self.assertTrue(result["normal_parity_result"]["verification"])

    def test_file_blockers_are_precise_and_intent_is_protected(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zfa(Path(folder))
        self.assertEqual("FILE_READ_PERMISSION", result["read_failure_result"]["blocker"])
        self.assertEqual("FILE_WRITE_PERMISSION", result["write_failure_result"]["blocker"])
        self.assertEqual("PATH_FAILURE", result["path_failure_result"]["blocker"])
        self.assertEqual("VERIFICATION_FAILURE", result["partial_write_result"]["blocker"])
        self.assertTrue(result["read_failure_result"]["intent_unchanged"])

    def test_integrity_resume_duplicate_and_stale_guards_hold(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zfa(Path(folder))
        self.assertTrue(result["frozen_spec_mutation_result"]["stopped"])
        self.assertEqual(0, result["duplicate_resume_result"]["duplicate_accepted_executions"])
        self.assertEqual("REJECTED", result["stale_owner_result"]["stale_owner_commit"])
        self.assertFalse(result["partial_write_result"]["false_commit"])

    def test_rollback_and_waiting_branch_isolation_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zfa(Path(folder))
        self.assertTrue(result["rollback_test_result"]["pass"])
        self.assertTrue(result["rollback_test_result"]["legacy_still_usable"])
        self.assertTrue(result["waiting_branch_isolation"]["selected_branch_only"])

    def test_adoption_is_supported_but_not_core_or_production_wide(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zfa(Path(folder))
        self.assertEqual("ZFBR_WORKFLOW_ADOPTION_SUPPORTED", result["final_decision"])
        self.assertEqual("LOW", result["complexity_delta"]["classification"])
        self.assertIn("PRODUCTION_WIDE_ADOPTION_NOT_AUTHORIZED", result["production_status"])


if __name__ == "__main__": unittest.main()
