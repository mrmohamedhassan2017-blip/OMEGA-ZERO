import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import (generate_economic_bridge_candidates, operate_economic_bridge_cycle,
                               score_value_primitive, simulate_atomic_zeu_contracts)


class ZeroEconomicBridgeTests(unittest.TestCase):
    def test_candidates_have_complete_consumption_and_value_contract(self):
        candidates = generate_economic_bridge_candidates()
        self.assertGreaterEqual(len(candidates), 7)
        required = {"customer_consumer", "actually_consumed", "scarcity_value", "value_verification",
                    "machine_to_machine_feasibility", "human_dependency", "marginal_cost", "automation_potential",
                    "repeatability", "external_settlement_options", "legal_authority_friction",
                    "time_to_first_real_value", "eva", "evsi", "failure_modes", "kill_criteria"}
        self.assertTrue(all(required <= set(item) for item in candidates))

    def test_scoring_is_not_identifier_hardcoded(self):
        candidate = dict(generate_economic_bridge_candidates()[0]); candidate["id"] = "renamed"; candidate["eva"] = 0
        self.assertNotEqual(generate_economic_bridge_candidates()[0]["score"], score_value_primitive(candidate)["score"])

    def test_atomic_zeu_contracts_never_create_real_value(self):
        result = simulate_atomic_zeu_contracts()
        self.assertEqual("SIMULATION_ONLY", result["mode"]); self.assertEqual(0, result["real_economic_value_kwd"])
        self.assertTrue(all(item["mission_value_delta_kwd"] == 0 for item in result["scenarios"]))
        double = next(item for item in result["scenarios"] if item["scenario"] == "double-spend")
        self.assertEqual("REJECTED", double["second_settlement"])

    def test_cycle_freezes_external_consumption_without_money_rail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); zero = root / ".omega" / "zero"; zero.mkdir(parents=True)
            state = {"global_state": "WAITING_AUTHORIZATION", "branches": [
                {"id": "inbound-evidence", "state": "PUBLISHED_WAITING_EXTERNAL_EVIDENCE"},
                {"id": "zero-discovery-001", "state": "WAITING_AUTHORIZATION"}]}
            (zero / "state.json").write_text(json.dumps(state), encoding="utf-8")
            result = operate_economic_bridge_cycle(root)
            self.assertFalse(result["execution"]["external_action_performed"])
            self.assertFalse(result["execution"]["real_money_rail_implemented"])
            self.assertIsNone(result["execution"]["authorization_case"])
            self.assertEqual(0, result["real_economic_value_kwd"])
            self.assertEqual("NOT_JUSTIFIED", result["native_real_token"])


if __name__ == "__main__":
    unittest.main()
