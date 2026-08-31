import json
import tempfile
import unittest
from pathlib import Path

from omega.cyber_external_evaluation import (
    EVALUATORS_REQUIRED,
    build_external_challenges,
    external_evaluation_status,
    freeze_external_evaluation_packet,
    validate_evaluator_submission,
)


class CyberExternalEvaluationTests(unittest.TestCase):
    def test_packet_freezes_protocol_and_challenges_before_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = freeze_external_evaluation_packet(root)
            packet = Path(status["packet_path"])
            self.assertEqual("READY_FOR_INDEPENDENT_EVALUATOR", status["packet_state"])
            self.assertEqual(14, status["challenges"])
            self.assertEqual(14, status["domains_covered"])
            self.assertEqual(0, status["evaluators_accepted"])
            self.assertTrue((packet / "evaluation_protocol.json").exists())
            self.assertTrue((packet / "frozen_challenges.json").exists())
            self.assertTrue((packet / "submission.schema.json").exists())
            self.assertEqual(64, len(status["external_evaluation_spec_hash"]))
            self.assertEqual(64, len(status["external_challenge_set_hash"]))

    def test_challenges_are_blind_and_high_depth(self):
        challenges = build_external_challenges()
        self.assertEqual(14, len(challenges))
        self.assertTrue(all(case["blinding"]["ground_truth_hidden_from_candidate"] for case in challenges))
        self.assertTrue(any(case["case_class"] == "conflicting_evidence" for case in challenges))
        self.assertTrue(any(case["case_class"] == "benign_false_lead" for case in challenges))
        self.assertTrue(all("verification_plan" in case["expected_output_fields"] for case in challenges))

    def test_fake_independence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = freeze_external_evaluation_packet(root)
            result = validate_evaluator_submission(root, {
                "evaluator_id": "ZERO_INTERNAL_EVALUATOR",
                "evaluation_session_id": "session-1",
                "relationship_to_project": "INTERNAL",
                "independence_declaration": "I am independent",
                "protocol_hash": status["external_evaluation_spec_hash"],
                "challenge_set_hash": status["external_challenge_set_hash"],
                "overall_score": 1.0,
                "safety_score": 1.0,
                "critical_failures": [],
                "completed_at": "2026-08-31T00:00:00Z",
            })
            self.assertFalse(result["accepted"])
            self.assertIn("fake_or_non_independent_evaluator", result["rejection_reasons"])
            self.assertIn("relationship_not_independent", result["rejection_reasons"])

    def test_tampered_or_duplicate_submission_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = freeze_external_evaluation_packet(root)
            good = {
                "evaluator_id": "external-practitioner-1",
                "evaluation_session_id": "session-1",
                "relationship_to_project": "NONE",
                "independence_declaration": "No relationship to the project.",
                "protocol_hash": status["external_evaluation_spec_hash"],
                "challenge_set_hash": status["external_challenge_set_hash"],
                "overall_score": 0.9,
                "safety_score": 1.0,
                "critical_failures": [],
                "completed_at": "2026-08-31T00:00:00Z",
            }
            first = validate_evaluator_submission(root, good)
            duplicate = validate_evaluator_submission(root, good)
            tampered = validate_evaluator_submission(root, {**good, "evaluation_session_id": "session-2", "protocol_hash": "bad"})
            self.assertTrue(first["accepted"])
            self.assertFalse(duplicate["accepted"])
            self.assertIn("duplicate_evaluation_session", duplicate["rejection_reasons"])
            self.assertFalse(tampered["accepted"])
            self.assertIn("wrong_protocol_hash", tampered["rejection_reasons"])

    def test_promotion_requires_two_accepted_independent_evaluations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = freeze_external_evaluation_packet(root)
            for idx in range(EVALUATORS_REQUIRED):
                result = validate_evaluator_submission(root, {
                    "evaluator_id": f"external-practitioner-{idx}",
                    "evaluation_session_id": f"session-{idx}",
                    "relationship_to_project": "NONE",
                    "independence_declaration": "No relationship to the project.",
                    "protocol_hash": status["external_evaluation_spec_hash"],
                    "challenge_set_hash": status["external_challenge_set_hash"],
                    "overall_score": 0.9,
                    "safety_score": 1.0,
                    "critical_failures": [],
                    "completed_at": "2026-08-31T00:00:00Z",
                })
                self.assertTrue(result["accepted"])
            final = external_evaluation_status(root)
            self.assertEqual("INDEPENDENT_EVIDENCE_SUFFICIENT", final["zero_verdict"])
            self.assertTrue(final["promoted"])

    def test_results_are_append_only_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = freeze_external_evaluation_packet(root)
            validate_evaluator_submission(root, {
                "evaluator_id": "OWNER_SELF_TEST",
                "evaluation_session_id": "owner-session",
                "relationship_to_project": "OWNER",
                "independence_declaration": "owner",
                "protocol_hash": status["external_evaluation_spec_hash"],
                "challenge_set_hash": status["external_challenge_set_hash"],
                "overall_score": 1.0,
                "safety_score": 1.0,
                "critical_failures": [],
                "completed_at": "2026-08-31T00:00:00Z",
            })
            lines = (Path(status["packet_path"]) / "results.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(json.loads(line).get("accepted") is False for line in lines if line.strip()))


if __name__ == "__main__":
    unittest.main()
