import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import (generate_value_bridge_routes, operate_value_bridge_experiment,
                               record_value_bridge_publication, score_value_bridge_route)


class ZeroValueBridgeTests(unittest.TestCase):
    def _root(self, tmp: str) -> Path:
        root = Path(tmp); out = root / ".omega" / "zero"; out.mkdir(parents=True)
        state = {"global_state": "PARKED_NO_EXECUTABLE_ACTION", "branches": [
            {"id": "inbound-evidence", "state": "PUBLISHED_WAITING_EXTERNAL_EVIDENCE"}]}
        (out / "state.json").write_text(json.dumps(state), encoding="utf-8")
        (out / "inbound_experiment.json").write_text(json.dumps({"spec_hash": "frozen-123"}), encoding="utf-8")
        return root

    def test_value_unit_and_ladder_are_complete_and_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = operate_value_bridge_experiment(self._root(tmp))
            unit = result["value_unit"]
            self.assertTrue({"input", "work_performed", "output", "verification_method", "provenance",
                             "success_condition", "failure_condition", "marginal_resource_cost",
                             "expected_consumer_benefit"} <= set(unit))
            self.assertEqual([f"L{i}" for i in range(7)], [x["level"] for x in result["evidence_ladder"]])
            self.assertEqual("L0", result["current_real_evidence_level"])

    def test_provenance_excludes_owner_and_requires_utility(self):
        with tempfile.TemporaryDirectory() as tmp:
            rule = operate_value_bridge_experiment(self._root(tmp))["provenance_rule"]
            self.assertIn("mrmohamedhassan2017-blip", rule["independence"])
            self.assertIn("utility decision", rule["required"])
            self.assertIn("no view", rule["promotion_rule"])

    def test_existing_public_package_is_independently_consumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = operate_value_bridge_experiment(self._root(tmp))
            interface = result["minimum_interface"]
            self.assertIn("@159def24", interface["install"])
            self.assertIn("agent_runtime_audit", interface["invoke"])
            self.assertIn("OMEGA intervention is not required", interface["note"])

    def test_route_ranking_is_scored_not_identifier_hardcoded(self):
        routes = generate_value_bridge_routes(); changed = dict(routes[0]); changed["id"] = "renamed"; changed["eva"] = 0
        self.assertNotEqual(routes[0]["score"], score_value_bridge_route(changed)["score"])
        self.assertGreaterEqual(len(routes), 5)

    def test_internal_prep_only_creates_one_bounded_authority_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = operate_value_bridge_experiment(self._root(tmp))
            self.assertFalse(result["external_action_performed"])
            self.assertEqual("AUTHORIZATION_REQUIRED", result["authorization_case"]["status"])
            self.assertEqual(0, result["real_economic_value_kwd"])
            self.assertEqual("SIMULATION_ONLY", result["zeu"])
            self.assertEqual("UNPROVEN_RESEARCH_HYPOTHESIS", result["zeu_x"])
            self.assertEqual("frozen-123", result["preserved_inbound_frozen_hash"])

    def test_publication_record_consumes_authority_without_promoting_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp); out = root / ".omega" / "zero"
            result = operate_value_bridge_experiment(root)
            result["preserved_inbound_frozen_hash"] = "084d9cc1f6ef7e7f97b3ba480daf16df95e15df2607d1cc5b08298eb5d8eab87"
            (out / "value_bridge_experiment.json").write_text(json.dumps(result), encoding="utf-8")
            (out / "value_bridge_authority_case.json").write_text(json.dumps(result["authorization_case"]), encoding="utf-8")
            evidence = record_value_bridge_publication(root)
            self.assertEqual("CONSUMED_CLOSED", evidence["authorization_state"])
            self.assertTrue(evidence["external_action"]); self.assertFalse(evidence["external_evidence"])
            self.assertFalse(evidence["invocation"]); self.assertEqual(0, evidence["economic_value_kwd"])


if __name__ == "__main__":
    unittest.main()
