import tempfile
import unittest
from pathlib import Path

from omega.engine import Engine
from omega.store import Store


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.db")
        self.problem = self.store.create_problem("Launch", "Should we launch?")
        self.goal = self.store.add_node(self.problem["id"], "assumption", "Launch succeeds", 0.4)
        self.fact = self.store.add_node(self.problem["id"], "fact", "Prototype works", 0.9, ["test run"])
        self.unknown = self.store.add_node(self.problem["id"], "unknown", "Demand exists", 0.2)
        self.store.add_edge(self.problem["id"], self.goal["id"], self.fact["id"], "supports")
        self.store.add_edge(self.problem["id"], self.goal["id"], self.unknown["id"], "depends_on")
        self.engine = Engine(self.store.graph(self.problem["id"]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_graph_persists_typed_nodes_and_edges(self):
        graph = self.store.graph(self.problem["id"])
        self.assertEqual(3, len(graph["nodes"])); self.assertEqual(2, len(graph["edges"]))

    def test_why_finds_unknown_gap(self):
        result = self.engine.why(self.goal["id"])
        self.assertEqual(self.unknown["id"], result["unresolved_gaps"][0]["id"])

    def test_break_it_prioritizes_fragile_dependency(self):
        result = self.engine.break_it()
        self.assertEqual(self.unknown["id"], result["attack_order"][0]["node"]["id"])

    def test_prove_it_builds_test_plan(self):
        self.assertGreaterEqual(len(self.engine.prove_it(self.goal["id"])["test_plan"]), 2)

    def test_what_if_propagates_to_dependents(self):
        impacted = self.engine.what_if(self.unknown["id"], False)["impacted"]
        self.assertEqual(self.goal["id"], impacted[0]["node"]["id"])

    def test_dependency_cycles_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.store.add_edge(self.problem["id"], self.unknown["id"], self.goal["id"], "depends_on")

    def test_self_edges_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "self-referential"):
            self.store.add_edge(self.problem["id"], self.goal["id"], self.goal["id"], "relates_to")

    def test_node_can_record_evidence_and_resolution_status(self):
        updated = self.store.update_node(self.unknown["id"], confidence=0.8,
                                         evidence=[{"source": "experiment-1"}], status="resolved")
        self.assertEqual("resolved", updated["status"])
        self.assertEqual("experiment-1", updated["evidence"][0]["source"])

    def test_validation_rejects_fact_without_evidence(self):
        unsupported = self.store.add_node(self.problem["id"], "fact", "Unsupported claim", 0.7)
        result = Engine(self.store.graph(self.problem["id"])).validate()
        self.assertFalse(result["valid"])
        self.assertIn(unsupported["id"], [i["node_id"] for i in result["issues"]])


if __name__ == "__main__":
    unittest.main()
