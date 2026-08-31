import tempfile
import unittest
from pathlib import Path

from omega.experiment_override import enable_experiment_override
from omega.mission_control import (create_mission, execute_mission, list_missions, parse_command,
                                   route_operator_command, transition_mission, verify_mission,
                                   zero_challenge)


class MissionControlTests(unittest.TestCase):
    def test_command_routing_supports_zero_omega_and_arabic_status(self):
        self.assertEqual(parse_command("ZERO, status").target_role, "ZERO")
        self.assertEqual(parse_command("OMEGA, execute mission-12345678").normalized_intent, "EXECUTE")
        self.assertEqual(parse_command("الحالة").normalized_intent, "STATUS")

    def test_mission_creation_persistence_and_listing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Improve system reliability")
            self.assertEqual(mission.status, "DRAFT")
            self.assertEqual(len(list_missions(root)), 1)
            result = route_operator_command(root, "SHOW MISSIONS")
            self.assertEqual(result["result"]["mission_count"], 1)

    def test_legal_and_illegal_transitions_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Improve operator console")
            mission = transition_mission(root, mission.mission_id, "PROPOSED")
            self.assertEqual(mission.status, "PROPOSED")
            with self.assertRaises(ValueError):
                transition_mission(root, mission.mission_id, "VERIFIED")

    def test_zero_cannot_verify_without_evidence_and_omega_claim_remains_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Run bounded internal preparation")
            verdict = verify_mission(root, mission.mission_id)
            self.assertEqual(verdict.verdict_type, "UNVERIFIED")
            self.assertTrue(verdict.missing_evidence)

    def test_zero_challenge_surfaces_missing_evidence_and_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Declare the entire system production ready")
            verdict = zero_challenge(root, mission.mission_id)
            self.assertIn(verdict.verdict_type, {"CONDITIONAL", "BLOCKED"})
            self.assertIn("completion evidence", verdict.missing_evidence)
            self.assertTrue(any("self-verify" in item for item in verdict.conditions))

    def test_execute_denied_without_authority_then_allowed_by_internal_experiment_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Run internal host verification")
            denied = execute_mission(root, mission.mission_id)
            self.assertFalse(denied["executed"])
            self.assertEqual(denied["state"], "BLOCKED")
            enable_experiment_override(root, task_id=mission.mission_id)
            allowed = execute_mission(root, mission.mission_id)
            self.assertTrue(allowed["executed"])
            self.assertEqual(allowed["authorization"]["authority_source"], "EXPERIMENT_OVERRIDE")
            self.assertFalse(allowed["route"]["selected_route"]["execution_performed"])

    def test_verification_with_evidence_reaches_zero_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission = create_mission(root, "Create a verifiable mission record")
            verdict = verify_mission(root, mission.mission_id, evidence_ref="host-verification-pass")
            self.assertEqual(verdict.verdict_type, "VERIFIED")


if __name__ == "__main__":
    unittest.main()

