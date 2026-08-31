import json
import tempfile
import unittest
from pathlib import Path

from omega.zero_kernel import (WORK_ORDER_STAGES, generate_public_problem_candidates,
                               operate_counterparty_cycle, score_counterparty_problem,
                               validate_work_order, record_counterparty_comment)


class ZeroCounterpartyTests(unittest.TestCase):
    def _root(self, tmp: str) -> Path:
        root = Path(tmp); out = root / ".omega" / "zero"; out.mkdir(parents=True)
        (out / "state.json").write_text(json.dumps({"global_state": "RUNNING", "branches": []}), encoding="utf-8")
        return root

    def test_problem_candidates_are_problem_first_and_complete(self):
        candidates = generate_public_problem_candidates()
        self.assertGreaterEqual(len(candidates), 5)
        required = {"problem_id", "public_source", "problem_statement", "evidence_reference", "affected_system",
                    "frequency", "attempted_solutions", "capability_match", "counterparty", "uncertainty", "confidence"}
        self.assertTrue(all(required <= set(x) for x in candidates))
        self.assertTrue(all(x["semantic_boundary"] == "PUBLIC_PROBLEM_NOT_DEMAND" for x in candidates))

    def test_scoring_is_not_identifier_hardcoded_and_rejects_weak_fit(self):
        candidate = dict(generate_public_problem_candidates()[0]); candidate["problem_id"] = "renamed"; candidate["capability_match"] = .1
        result = score_counterparty_problem(candidate)
        self.assertEqual("REJECTED_WEAK_MATCH", result["qualification"])

    def test_work_order_schema_and_lifecycle_are_strict(self):
        self.assertEqual("OBSERVED_PROBLEM", WORK_ORDER_STAGES[0]); self.assertEqual("SETTLED", WORK_ORDER_STAGES[-1])
        self.assertIn("premature_settlement", validate_work_order({"stage": "PROPOSED_WORK_ORDER", "settlement_state": "PAID"}))

    def test_cycle_proposes_but_never_accepts_or_contacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = operate_counterparty_cycle(self._root(tmp))
            order = result["proposed_work_order"]
            self.assertEqual("PROPOSED_WORK_ORDER", order["stage"]); self.assertFalse(order["accepted"])
            self.assertFalse(result["external_action_performed"]); self.assertEqual("AUTHORIZATION_REQUIRED", result["authorization_case"]["status"])
            self.assertEqual("L0", result["current_value_level"]); self.assertEqual(0, result["real_economic_value_kwd"])

    def test_povu_and_zeu_never_create_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = operate_counterparty_cycle(self._root(tmp))
            self.assertEqual("UNPROVEN_RESEARCH_PRIMITIVE", result["povu"]["status"])
            self.assertFalse(result["povu"]["value_created"]); self.assertEqual([], result["povu"]["satisfied"])
            self.assertEqual("SIMULATION_ONLY", result["zeu"]); self.assertEqual("NOT_JUSTIFIED", result["native_real_token"])

    def test_comment_consumes_authority_without_promoting_work_or_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp); operate_counterparty_cycle(root)
            evidence = record_counterparty_comment(root)
            self.assertEqual("REAL_EXTERNAL_ACTION", evidence["event"]); self.assertEqual("NO_RESPONSE", evidence["response"])
            self.assertFalse(evidence["external_evidence"]); self.assertEqual(0, evidence["economic_value_kwd"])
            order = json.loads((root / ".omega" / "zero" / "proposed_work_order.json").read_text())
            self.assertEqual("PROPOSED_WORK_ORDER", order["stage"]); self.assertFalse(order["accepted"])
            self.assertTrue(order["causal_value_record"]["marginal_utility"].startswith("UNKNOWN"))


if __name__ == "__main__":
    unittest.main()
