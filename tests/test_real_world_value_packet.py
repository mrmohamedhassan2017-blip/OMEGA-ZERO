import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.real_world_value_deep import (
    B3_CONFIGURATION_FIELDS,
    INCIDENT_DATA_FIELDS,
    OPERATOR_TRACE_FIELDS,
    VERIFICATION_CRITERION_FIELDS,
    authority_envelope,
    blind_transform_spec,
    freeze_incident_packet,
    initial_contact_packet,
    packet_fixture_results,
    packet_red_team_report,
    participant_guide,
    record_packet_hardening_host_verification,
    run_deep_cycle,
    run_packet_hardening,
    validate_b3_configuration,
    validate_blind_transform,
    validate_incident_data,
    validate_incident_packet,
    validate_operator_trace,
    validate_verification_criterion,
)


class RealWorldValuePacketTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        output = root / ".omega" / "zero"
        output.mkdir(parents=True)
        (root / "PROJECT_STATE.md").write_text(
            "version: 0.21.0\ncurrent_milestone: V0.30 External Evaluator Evidence Collection\n",
            encoding="utf-8",
        )
        (root / "NEXT_TASK.md").write_text("status: waiting_external_evidence\n", encoding="utf-8")
        (output / "zrwve_frontier_cycle_0002.json").write_text(
            json.dumps({"final_result": "NO_UNDEFEATED_OPPORTUNITY_FOUND"}), encoding="utf-8"
        )
        (output / "zrwve_frontier_experiment_0002.json").write_text(
            json.dumps({"result": "KILLED_MULTI_BASELINE_PARITY"}), encoding="utf-8"
        )

    def packet(self, fixture_id: str = "F1") -> dict:
        with tempfile.TemporaryDirectory() as directory:
            # The fixture report is the public constructor's stable test oracle.
            # Reconstructing through the report keeps tests independent of private helpers.
            rows = packet_fixture_results()["rows"]
        self.assertTrue(any(row["fixture_id"] == fixture_id for row in rows))
        # A compact qualifying packet used for schema-level tests.
        incident = {field: "UNKNOWN" for field in INCIDENT_DATA_FIELDS}
        incident.update({
            "incident_id_or_local_alias": fixture_id,
            "incident_date_or_time_window": "2025-01-15T10:00Z",
            "system_or_stack": "sanitized-dataflow", "orchestrator": "workflow-engine",
            "affected_workflow": "daily-reconciliation", "workflow_purpose": "bounded incident",
            "failure_trigger": "worker interruption", "expected_state": "checkpoint accepted",
            "observed_state": "state/effect diverged", "last_known_good_state": "checkpoint-7",
            "persisted_orchestrator_state": "checkpoint-7", "actual_external_state": "effect-pending",
            "partial_outputs_or_side_effects": ["redacted-effect"], "checkpoint_state": "checkpoint-7",
            "retry_or_replay_state": "retry-eligible", "downstream_effects": "held",
            "manual_intervention_occurred": True, "final_outcome": "safe resume",
            "sanitization_status": "PASS", "participant_confidence": "HIGH", "unknown_fields": [],
            "real_incident": True,
        })
        actual = {field: "UNKNOWN" for field in B3_CONFIGURATION_FIELDS}
        actual.update({
            "incident_id_or_local_alias": fixture_id, "b3_tool_or_system": "workflow-engine",
            "state_backend": "durable-store", "checkpointing_configuration": "checkpoint-7",
            "retry_policy": "bounded-retry", "transaction_or_idempotency_controls": "idempotency-key",
            "timeouts": "10m", "failure_handling": "pause-and-reconcile", "replay_policy": "manual-review",
            "observability": "state/effect metrics", "alerting": "on-call", "runbook_present": True,
            "human_review_present": True, "custom_recovery_automation": "reconcile-script",
            "manual_reconciliation": "cross-system check", "known_missing_control": "effect receipt",
            "configuration_unknown_fields": [],
        })
        counter = dict(actual)
        counter["b3_tool_or_system"] = "workflow-engine-plus-receipt"
        trace = {field: "UNKNOWN" for field in OPERATOR_TRACE_FIELDS}
        trace.update({
            "trace_step_id": "1", "relative_time": "T+0", "system_inspected": "state-store",
            "information_observed": "checkpoint/effect conflict", "belief_before": "resume safe",
            "belief_after": "hold replay", "action_taken": "hold replay", "why_action_was_taken": "avoid duplicate",
            "alternatives_considered": ["resume", "rollback"], "risk_being_avoided": "duplicate effect",
            "manual_or_automated": "MANUAL", "wait_required": True, "approval_required": False,
            "evidence_used": ["checkpoint"], "output": "safe decision pending", "unknown_or_uncertain": [],
            "decision_required": "SAFE_TO_RESUME", "evidence_missing": "effect receipt",
            "conflicting_states": ["worker", "effect"], "unsafe_automatic_action": "replay before check",
            "wrong_decision_consequence": "duplicate effect", "confidence_reason": "cross-check",
        })
        verification = {field: "UNKNOWN" for field in VERIFICATION_CRITERION_FIELDS}
        verification.update({
            "verification_target": "safe resume", "verification_signal": "effect receipt",
            "acceptance_condition": "all sources agree", "reject_condition": "any conflict",
            "source_of_truth": "participant system state plus deterministic check",
            "systems_cross_checked": ["orchestrator", "state-store", "effect-store"],
            "side_effect_validation": "receipt", "data_validation": "checksum",
            "downstream_validation": "held state", "replay_safety_validation": "idempotency key",
            "human_approval_if_any": "operator signoff", "final_completion_criterion": "three sources agree",
        })
        return {
            "incident_data": incident, "b3_actual": actual,
            "b3_strongest_reasonable_counterfactual": counter, "operator_trace": [trace],
            "verification_criterion": verification,
            "provenance": {"independence": True, "non_owner": True, "non_omega": True, "non_test_actor": True, "attributable": True},
            "sanitization_status": "PASS", "consequential_decision": {"decision": "SAFE_TO_RESUME", "value": "NO"},
            "decision_time_information": {"checkpoint": "checkpoint-7", "observed_conflict": "worker-effect", "evidence_cutoff": "T+0"},
            "outcome_verification": {"actual_result": "reconciled", "post_recovery_state": "consistent", "outcome": "safe"},
        }

    def test_schema_contracts_expose_all_mandatory_fields(self):
        from omega.real_world_value_deep import b3_configuration_schema, incident_data_schema, operator_trace_schema, verification_criterion_schema
        self.assertTrue(set(INCIDENT_DATA_FIELDS) <= set(incident_data_schema()["required_fields"]))
        self.assertTrue(set(B3_CONFIGURATION_FIELDS) <= set(b3_configuration_schema()["required_fields"]))
        self.assertTrue(set(OPERATOR_TRACE_FIELDS) <= set(operator_trace_schema()["required_fields"]))
        self.assertTrue(set(VERIFICATION_CRITERION_FIELDS) <= set(verification_criterion_schema()["required_fields"]))

    def test_incident_requires_real_sanitized_data_but_allows_unknowns(self):
        result = validate_incident_data(self.packet()["incident_data"])
        self.assertTrue(result["valid"])
        self.assertTrue(result["unknown_fields_preserved"])
        invalid = dict(self.packet()["incident_data"])
        invalid["real_incident"] = False
        self.assertFalse(validate_incident_data(invalid)["valid"])

    def test_opinion_only_and_generic_story_fail_closed(self):
        self.assertFalse(validate_incident_packet({"opinion": "This sounds useful."})["valid"])
        self.assertFalse(validate_incident_packet({"incident_data": {"failure": "generic story"}})["valid"])

    def test_b3_actual_and_counterfactual_are_separate(self):
        result = validate_b3_configuration(self.packet())
        self.assertTrue(result["valid"])
        self.assertTrue(result["separated"])
        same = self.packet(); same["b3_strongest_reasonable_counterfactual"] = dict(same["b3_actual"])
        self.assertFalse(validate_b3_configuration(same)["valid"])

    def test_operator_trace_captures_order_and_judgment(self):
        result = validate_operator_trace(self.packet()["operator_trace"])
        self.assertTrue(result["valid"])
        self.assertTrue(result["judgment_capture"])
        self.assertEqual(1, result["step_count"])

    def test_verification_requires_external_source_of_truth(self):
        self.assertTrue(validate_verification_criterion(self.packet()["verification_criterion"])["valid"])
        invalid = dict(self.packet()["verification_criterion"]); invalid["source_of_truth"] = "ZERO confidence"
        self.assertFalse(validate_verification_criterion(invalid)["valid"])

    def test_causal_linkage_and_decision_are_required(self):
        packet = self.packet()
        self.assertTrue(validate_incident_packet(packet)["valid"])
        packet["b3_actual"]["incident_id_or_local_alias"] = "other"
        result = validate_incident_packet(packet)
        self.assertFalse(result["valid"])
        self.assertFalse(result["causal_linkage"])

    def test_information_and_outcome_sets_are_separate_and_freezable(self):
        packet = self.packet()
        result = validate_incident_packet(packet)
        self.assertTrue(result["decision_time_information_set_freezable"])
        self.assertTrue(result["outcome_verification_set_freezable"])
        self.assertTrue(result["information_sets_separate"])
        frozen = freeze_incident_packet(packet)
        self.assertNotEqual(frozen["decision_information_set_hash"], frozen["outcome_verification_set_hash"])
        self.assertTrue(frozen["packet_hash"])

    def test_blind_transform_freezes_all_outcomes_without_winner(self):
        spec = blind_transform_spec()
        self.assertTrue(validate_blind_transform(spec))
        self.assertEqual({"B3_WINS", "ZERO_WINS", "PARITY", "INCONCLUSIVE"}, set(spec["outcomes"]))
        tampered = dict(spec); tampered["arms"] = ["ZERO_WINS"]
        self.assertFalse(validate_blind_transform(tampered))

    def test_participant_guide_and_contact_are_non_leading_and_privacy_safe(self):
        guide = participant_guide(); contact = initial_contact_packet()
        self.assertTrue(guide["negative_result_is_useful"])
        self.assertFalse(guide["opinion_alone_counts"])
        self.assertTrue(contact["optional_participation"])
        self.assertNotIn("Would you use", contact["message"])
        self.assertTrue(contact["no_external_write_executed"])

    def test_fixture_matrix_only_allows_f1_f9_f10_structural_pass(self):
        report = packet_fixture_results()
        self.assertTrue(report["test_only"])
        self.assertTrue(report["only_allowed_structural_passes"])
        self.assertEqual({"F1", "F9", "F10"}, set(report["structural_pass_ids"]))
        self.assertEqual(10, len(report["rows"]))

    def test_red_team_covers_required_attacks(self):
        report = packet_red_team_report()
        attacks = {row["attack"] for row in report["attacks"]}
        self.assertTrue({"opinion_only", "missing_b3", "missing_operator_steps", "secrets", "owner_actor", "duplicate_incident"} <= attacks)
        self.assertEqual("CONTAINED", report["result"])

    def test_authority_envelope_is_narrow_and_closed(self):
        envelope = authority_envelope()
        self.assertFalse(envelope["external_action_authorized"])
        self.assertEqual(3, envelope["max_qualified_participants"])
        self.assertEqual(1, envelope["max_clarifications_per_participant"])
        self.assertTrue(envelope["no_financial_authority"])
        self.assertTrue(envelope["no_secret_request"])

    def test_packet_cycle_is_local_idempotent_and_no_external_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.make_repository(root)
            run_deep_cycle(root)
            with patch("subprocess.run", side_effect=AssertionError("subprocess called")), patch("urllib.request.urlopen", side_effect=AssertionError("network called")):
                result = run_packet_hardening(root)
                replay = run_packet_hardening(root)
            self.assertEqual("READY_FOR_OWNER_AUTHORIZATION", result["final_packet_result"])
            self.assertEqual(0, result["external_write_executed"])
            self.assertTrue(replay["idempotent_replay"])
            self.assertTrue((root / ".omega" / "zero" / "zrwve_t2_authority_envelope.json").is_file())

    def test_packet_host_verification_updates_memory_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.make_repository(root); run_deep_cycle(root); run_packet_hardening(root)
            updated = record_packet_hardening_host_verification(root, {"status": "PASS", "packet": "11/11"})
            memory = json.loads((root / ".omega" / "zero" / "zrwve_packet_hardening_memory.json").read_text())
            host = json.loads((root / ".omega" / "zero" / "zrwve_packet_hardening_host_verification_0001.json").read_text())
            self.assertEqual(updated["test_results"]["status"], "PASS")
            self.assertEqual(memory["source_cycle_hash"], host["cycle_hash"])

    def test_packet_cycle_preserves_zero_and_v030_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.make_repository(root); run_deep_cycle(root)
            result = run_packet_hardening(root)
        self.assertEqual("L0", result["current_evidence_level"])
        self.assertEqual(0, result["verified_net_economic_value_kwd"])
        self.assertEqual("PASSIVE_PRODUCTION", result["wake_plane_mode"])
        self.assertEqual("SHADOW", result["capability_router_mode"])
        self.assertEqual("LEGACY", result["global_production_default"])


if __name__ == "__main__":
    unittest.main()
