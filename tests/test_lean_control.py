import tempfile
import unittest
from pathlib import Path

from omega.lean_control import run_lzp


class LeanControlTests(unittest.TestCase):
    def _run(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return run_lzp(Path(folder.name))

    def test_all_required_scenarios_have_decision_and_transition_parity(self):
        result = self._run()
        self.assertEqual(17, result["decision_parity"]["total"])
        self.assertEqual(17, result["decision_parity"]["passed_scenarios"])
        self.assertEqual("YES", result["state_transition_parity"])

    def test_authority_verification_and_resource_invariants_hold(self):
        result = self._run()
        self.assertEqual(0, result["authority_results"]["violations"])
        self.assertTrue(result["verification_results"]["host_authoritative"])
        self.assertEqual("TIMED_OUT_SAFE", result["resource_results"]["bounded_timeout"])
        self.assertTrue(all(result["invariant_set"].values()))

    def test_recovery_continuity_park_wake_and_deduplication_hold(self):
        result = self._run()
        self.assertTrue(all(result["recovery_results"].values()))
        self.assertTrue(result["continuity_results"]["waiting_branch_not_system"])
        self.assertEqual("BLOCK_DUPLICATE", result["failure_injection_results"]["DUPLICATE_EXECUTION_RISK"])

    def test_models_are_escalated_only_for_novel_state(self):
        result = self._run()
        self.assertEqual("NECESSARY", result["model_escalation_result"]["classification"])
        self.assertEqual(1, result["model_escalation_result"]["invoked"])
        self.assertEqual(0, result["model_escalation_result"]["normal_control_invocations"])

    def test_result_is_reversible_and_does_not_authorize_migration(self):
        result = self._run()
        self.assertEqual("LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION", result["final_result"])
        self.assertEqual("SUPPORTED", result["zak_simplification_result"])
        self.assertEqual("SUPPORTED", result["zrl_simplification_result"])
        self.assertIn("production code/state/schema unchanged", result["rollback_status"])


if __name__ == "__main__":
    unittest.main()
