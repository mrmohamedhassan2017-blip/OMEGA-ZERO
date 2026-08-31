import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omega.real_world_value_frontier import (
    PUBLIC_FRONTIER_EVIDENCE,
    baseline_adversary,
    execute_frontier_experiment,
    freeze_frontier_experiment,
    frontier_search_justification,
    frontier_status,
    killed_wedge_exclusion_map,
    rank_frontier,
    run_frontier_cycle,
    serious_candidates,
    validate_frontier_experiment,
)


class RealWorldValueFrontierTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        output = root / ".omega" / "zero"
        output.mkdir(parents=True)
        (root / "PROJECT_STATE.md").write_text("version: 0.21.0\nL0\n", encoding="utf-8")
        (root / "NEXT_TASK.md").write_text("status: waiting_external_evidence\n", encoding="utf-8")
        history = {
            "zopd_cycle_0001.json": {"state": "DISCOVERY_COMPLETE_NO_WINNER"},
            "zmi_cycle_0001.json": {"state": "WAITING_EXTERNAL"},
            "veh_001_comparison.json": {"state": "BASELINE_PARITY"},
            "ccs_001_cycle.json": {"state": "CCS_BASELINE_PARITY"},
            "zdoa_001_result.json": {"final_comparative_result": "ZERO_BASELINE_PARITY"},
            "zad_cycle_0001.json": {"state": "NO_DEMONSTRATED_ADVANTAGE"},
            "zrwve_cycle_0002.json": {"final_result": "PRIMARY_VALUE_HYPOTHESIS_KILLED_BASELINE_PARITY"},
            "capability_fabric_cycle_0001.json": {"router_mode": "SHADOW"},
            "development_governor_cycle_0001.json": {"state": "PARKED"},
        }
        for name, payload in history.items():
            (output / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_frontier_search_is_justified_before_adjacent_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            result = frontier_search_justification(root)
        self.assertTrue(result["frontier_search_was_justified"])
        self.assertIn("GitOps partial reconciliation", result["uncovered_adjacent_classes"])

    def test_prior_killed_wedges_are_complete_and_never_reopened(self):
        rows = killed_wedge_exclusion_map(Path("."))
        ids = {row["wedge_id"] for row in rows}
        self.assertIn("RUNTIME_DURABILITY_RECEIPT", ids)
        self.assertIn("EXACTLY_ONCE_CAUSAL_EXECUTION", ids)
        self.assertTrue(all(not row["reopened"] for row in rows))
        self.assertTrue(all(row["strongest_baseline"] for row in rows))
        self.assertTrue(all(row["reopen_condition"] for row in rows))

    def test_evidence_corpus_is_diverse_and_never_a_zero_signal(self):
        self.assertGreaterEqual(len({row["project"] for row in PUBLIC_FRONTIER_EVIDENCE}), 7)
        self.assertGreaterEqual(len({row["actor_class"] for row in PUBLIC_FRONTIER_EVIDENCE}), 7)
        self.assertGreaterEqual(len({row["year"] for row in PUBLIC_FRONTIER_EVIDENCE}), 6)
        self.assertTrue(all(row["independent_of_zero"] for row in PUBLIC_FRONTIER_EVIDENCE))
        self.assertTrue(all(not row["signal_to_zero"] for row in PUBLIC_FRONTIER_EVIDENCE))
        self.assertTrue(all(not row["authority_effect"] for row in PUBLIC_FRONTIER_EVIDENCE))

    def test_candidate_cap_and_required_record_fields(self):
        candidates = serious_candidates()
        required = {
            "opportunity_id", "actor", "context", "problem", "real_evidence", "workaround",
            "strongest_baseline", "baseline_cost", "consequential_decision",
            "zero_differential_claim", "expected_decision_delta", "expected_attention_delta",
            "measurability", "authority_burden", "time_to_truth", "build_cost",
            "external_dependence", "negative_evidence", "cheapest_falsification",
        }
        self.assertLessEqual(len(candidates), 12)
        self.assertGreaterEqual(len(candidates), 5)
        self.assertTrue(all(required <= set(row) for row in candidates))
        self.assertTrue(all(row["negative_evidence"] for row in candidates))

    def test_ranking_is_transparent_and_not_identifier_order(self):
        candidates = serious_candidates()
        ranking = rank_frontier(candidates)
        self.assertEqual("F-GITOPS-REVISION-CONTINUITY", ranking[0]["opportunity_id"])
        self.assertIn("benefit_contributions", ranking[0])
        self.assertIn("penalty_contributions", ranking[0])
        self.assertNotEqual(sorted(row["opportunity_id"] for row in ranking), [row["opportunity_id"] for row in ranking])

    def test_baseline_adversary_uses_all_required_baseline_classes(self):
        result = baseline_adversary(serious_candidates()[0])
        for field in ("configuration", "deterministic_logic", "transactional_boundary", "idempotency", "monitoring", "human_batch_review", "existing_platform"):
            self.assertIn(field, result)
        self.assertEqual("ELIMINATED_BY_STRONG_BASELINE", result["result"])

    def experiment(self):
        return freeze_frontier_experiment(
            experiment_id="F-1", hypothesis="ZERO changes decision", null_hypothesis="B3 same",
            actor="operator", decision="resume?", baseline=("B1", "B2", "B3"),
            zero_primitive="receipt",
            frozen_scenarios=({
                "scenario_id": "S1", "source": "primary", "facts": ["fact"],
                "b3_decision": "REPAIR", "zero_decision": "REPAIR",
                "baseline_human_steps": 1, "zero_human_steps": 1,
                "baseline_manual_checks": 1, "zero_manual_checks": 1,
                "baseline_reconstruction_minutes": 1, "zero_reconstruction_minutes": 1,
            },),
            primary_metric="delta", decision_delta_threshold="2 cases",
            attention_delta_threshold="50 percent", complexity_threshold="20 percent",
            failure_threshold="same decision", time_budget="one cycle",
            resource_budget={"network_calls": 0},
            authority="INTERNAL_READ_ONLY_NO_EXTERNAL_EFFECT",
            abort_conditions=("threshold mutation",),
        )

    def test_frozen_frontier_experiment_integrity_and_tamper_detection(self):
        experiment = self.experiment()
        self.assertTrue(validate_frontier_experiment(experiment))
        experiment["decision_delta_threshold"] = "one easy case"
        self.assertFalse(validate_frontier_experiment(experiment))

    def test_frontier_experiment_rejects_external_authority(self):
        with self.assertRaises(ValueError):
            freeze_frontier_experiment(
                experiment_id="F", hypothesis="h", null_hypothesis="n", actor="a",
                decision="d", baseline=("B",), zero_primitive="z", frozen_scenarios=(),
                primary_metric="m", decision_delta_threshold="d", attention_delta_threshold="a",
                complexity_threshold="c", failure_threshold="f", time_budget="t",
                resource_budget={}, authority="EXTERNAL_WRITE", abort_conditions=(),
            )

    def test_historical_replay_proves_no_decision_attention_or_reliability_delta(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            result = run_frontier_cycle(root)
        self.assertEqual("NONE", result["decision_delta"]["status"])
        self.assertEqual("NONE", result["owner_attention_delta"]["status"])
        self.assertEqual("NONE", result["reliability_delta"]["status"])
        self.assertEqual("NOT_JUSTIFIED", result["complexity_delta"]["status"])

    def test_all_candidates_dying_is_accepted_and_engine_parks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            result = run_frontier_cycle(root)
        self.assertEqual("NO_UNDEFEATED_OPPORTUNITY_FOUND", result["final_result"])
        self.assertEqual("PARKED", result["value_engine_mode"])
        self.assertIsNone(result["surviving_candidate"])
        self.assertEqual([], result["authority_required"])
        self.assertEqual([], result["external_actions_performed"])

    def test_cycle_is_local_and_invokes_no_process_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            with patch.object(subprocess, "run", side_effect=AssertionError("process called")), patch(
                "urllib.request.urlopen", side_effect=AssertionError("network called")
            ):
                result = run_frontier_cycle(root)
        self.assertEqual(0, result["authority_violations"])
        self.assertEqual(0, result["verified_net_economic_value_kwd"])

    def test_cycle_persists_frozen_artifacts_and_replays_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            first = run_frontier_cycle(root)
            (root / "PROJECT_STATE.md").write_text(
                "version: 0.21.0\nL0\nDocumentation-only note.\n", encoding="utf-8"
            )
            second = run_frontier_cycle(root)
            output = root / ".omega" / "zero"
            self.assertTrue((output / "zrwve_frontier_cycle_0001.json").is_file())
            self.assertTrue((output / "zrwve_frontier_experiment_0001.json").is_file())
            self.assertTrue((output / "zrwve_killed_wedge_map.json").is_file())
            self.assertEqual(first["experiment_spec_hash"], second["experiment_spec_hash"])
            self.assertTrue(second["idempotent_replay"])
            self.assertFalse((output / "zrwve_frontier_cycle_0002.json").exists())

    def test_frontier_status_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            run_frontier_cycle(root)
            before = sorted((root / ".omega" / "zero").glob("zrwve_frontier_cycle_*.json"))
            status = frontier_status(root)
            after = sorted((root / ".omega" / "zero").glob("zrwve_frontier_cycle_*.json"))
        self.assertEqual("PARKED", status["value_engine_mode"])
        self.assertEqual("NONE", status["decision_delta"])
        self.assertEqual(before, after)

    def test_wake_capability_and_production_boundaries_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            result = run_frontier_cycle(root)
        self.assertEqual("PASSIVE_PRODUCTION", result["wake_plane_mode"])
        self.assertFalse(result["wake_plane_update"]["new_watcher_created"])
        self.assertEqual("SHADOW", result["capability_router_mode"])
        self.assertEqual("NONE", result["capability_fabric_observation"]["promotion"])
        self.assertEqual("LEGACY", result["global_production_default"])

    def test_red_team_contains_every_preregistered_attack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            red = run_frontier_cycle(root)["red_team_result"]
        self.assertEqual(13, red["attacks_contained"])
        self.assertEqual(0, red["false_external_evidence_promotions"])
        self.assertEqual(0, red["authority_violations"])
        self.assertEqual("PASS_FAIL_CLOSED", red["verdict"])


if __name__ == "__main__":
    unittest.main()
