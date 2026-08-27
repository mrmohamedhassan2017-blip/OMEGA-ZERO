import json
import tempfile
import unittest
from pathlib import Path

from omega.evaluation import (aggregate_records, prepare_blind_case, run_blind_case,
                              run_protocol_gate, score_reveal)
from omega.store import Store


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.tmp.name) / "eval.db")
        problem = self.store.create_problem("External case", "Blind ranking")
        weak = self.store.add_node(problem["id"], "unknown", "Weak premise", 0.1)
        self.store.add_node(problem["id"], "assumption", "Stronger premise", 0.8)
        self.bundle = self.store.export_problem(problem["id"])
        self.weak_key = next(node["key"] for node in self.bundle["payload"]["nodes"]
                             if node["statement"] == "Weak premise")
        self.other_key = next(node["key"] for node in self.bundle["payload"]["nodes"]
                              if node["statement"] == "Stronger premise")

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, evaluator="external-1"):
        return prepare_blind_case(self.bundle, {"expected_order": [self.weak_key, self.other_key],
                                                "evaluator_ref": evaluator}, salt="secret-salt")

    def test_public_case_contains_commitment_but_not_labels(self):
        prepared = self.prepare(); text = json.dumps(prepared["public_case"], sort_keys=True)
        self.assertNotIn("expected_order", text); self.assertNotIn("external-1", text)
        self.assertIn("label_commitment", prepared["public_case"])

    def test_prediction_and_reveal_produce_verified_metrics(self):
        prepared = self.prepare(); prediction = run_blind_case(prepared["public_case"])
        result = score_reveal(prepared["public_case"], prediction, prepared["private_reveal"])
        self.assertTrue(result["verified"]); self.assertTrue(result["metrics"]["top1"])
        self.assertEqual(1.0, result["metrics"]["pairwise_agreement"])

    def test_modified_reveal_is_rejected(self):
        prepared = self.prepare(); prediction = run_blind_case(prepared["public_case"])
        prepared["private_reveal"]["expected_order"].reverse()
        with self.assertRaisesRegex(ValueError, "commitment"):
            score_reveal(prepared["public_case"], prediction, prepared["private_reveal"])

    def test_modified_prediction_is_rejected(self):
        prepared = self.prepare(); prediction = run_blind_case(prepared["public_case"])
        prediction["predicted_order"].reverse()
        with self.assertRaisesRegex(ValueError, "prediction"):
            score_reveal(prepared["public_case"], prediction, prepared["private_reveal"])

    def test_verified_records_aggregate(self):
        records = []
        for evaluator in ("external-1", "external-2"):
            prepared = self.prepare(evaluator); prediction = run_blind_case(prepared["public_case"])
            records.append(score_reveal(prepared["public_case"], prediction, prepared["private_reveal"]))
        summary = aggregate_records(records)
        self.assertEqual(2, summary["records"]); self.assertEqual(2, summary["independent_evaluator_refs"])
        self.assertEqual(1.0, summary["metrics"]["top1_accuracy"])

    def test_protocol_gate(self):
        self.assertTrue(run_protocol_gate()["passed"])

    def test_verified_record_persists_once(self):
        prepared = self.prepare(); prediction = run_blind_case(prepared["public_case"])
        record = score_reveal(prepared["public_case"], prediction, prepared["private_reveal"])
        stored = self.store.record_evaluation(record)
        self.assertTrue(stored["stored"])
        self.assertEqual(1, len(self.store.list_evaluations()))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.store.record_evaluation(record)

    def test_unverified_record_is_rejected(self):
        prepared = self.prepare(); prediction = run_blind_case(prepared["public_case"])
        record = score_reveal(prepared["public_case"], prediction, prepared["private_reveal"])
        record["verified"] = False
        with self.assertRaisesRegex(ValueError, "verified"):
            self.store.record_evaluation(record)


if __name__ == "__main__":
    unittest.main()
