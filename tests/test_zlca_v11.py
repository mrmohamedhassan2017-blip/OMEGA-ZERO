import json
import tempfile
import unittest
from pathlib import Path

from omega.zlca_v11 import run_zlca_v11


class ZLCAV11Tests(unittest.TestCase):
    def test_refuses_synthetic_model_output_when_executor_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zlca_v11(Path(folder))
        self.assertEqual("INCONCLUSIVE", result["final_result"])
        self.assertEqual("MODEL_EXECUTOR_UNAVAILABLE_FOR_REAL_ESCALATION", result["genuine_blocker"])
        self.assertEqual(0, result["resource_results"]["model_call_count"])
        self.assertTrue(all(row["status"] == "NOT_EXECUTED" for row in result["model_escalation_results"]))

    def test_freezes_exactly_three_non_tailored_cases_and_safe_baselines(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_zlca_v11(Path(folder))
        self.assertEqual(3, len(result["zlca_model_frozen_spec"]["cases"]))
        self.assertEqual(64, len(result["spec_hash"]))
        self.assertEqual(0, result["decision_delta_results"]["useful"])
        self.assertEqual(0, result["safety_results"]["authority_violations"])

    def test_executor_contract_is_strict_and_proposals_are_not_verified_by_model(self):
        def executor(case):
            return {"interpretation": "bounded", "proposed_action": "PARK", "evidence_used": [case["id"]], "uncertainty": "HIGH", "missing_information": [], "expected_consequence": "no unsafe action"}
        with tempfile.TemporaryDirectory() as folder:
            result = run_zlca_v11(Path(folder), executor)
        self.assertEqual("PENDING_HOST_VERIFICATION", result["final_result"])
        self.assertEqual(3, result["resource_results"]["model_call_count"])
        self.assertTrue(result["verification_results"]["model_cannot_verify_itself"])

    def test_invalid_executor_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError): run_zlca_v11(Path(folder), lambda case: {"proposed_action": "EXECUTE"})


if __name__ == "__main__": unittest.main()
