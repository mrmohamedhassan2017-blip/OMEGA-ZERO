import tempfile
import unittest
import sqlite3
from pathlib import Path

from omega.engine import Engine
from omega.store import Store
from omega.evidence import evidence_strength, normalize_evidence
from omega.benchmark import run_ranking_benchmark
from omega.ontology import run_taxonomy_benchmark
from omega.operation_benchmark import run_operation_benchmark
from omega.scoring import ScoringProfile
from omega.sensitivity import run_sensitivity_benchmark


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.db")
        self.problem = self.store.create_problem("Launch", "Should we launch?")
        self.goal = self.store.add_node(self.problem["id"], "assumption", "Launch succeeds", 0.4)
        self.fact = self.store.add_node(self.problem["id"], "fact", "Prototype works", 0.9, ["test run"])
        self.unknown = self.store.add_node(self.problem["id"], "unknown", "Demand exists", 0.2)
        self.store.add_edge(self.problem["id"], self.fact["id"], self.goal["id"], "supports")
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

    def test_claim_profile_persists_and_drives_prove_it(self):
        node = self.store.add_node(
            self.problem["id"], "assumption", "Retention improves", 0.45,
            assumptions=["Users return voluntarily"],
            uncertainty="Cohort size may be too small",
            falsifier="Four-week retention stays below 10 percent",
        )
        reopened = Store(self.store.path).get_node(node["id"])
        self.assertEqual(["Users return voluntarily"], reopened["assumptions"])
        result = Engine(Store(self.store.path).graph(self.problem["id"])).prove_it(node["id"])
        self.assertEqual("Cohort size may be too small", result["declared_uncertainty"])
        self.assertEqual("Four-week retention stays below 10 percent", result["fail_condition"])
        self.assertIn("Attempt falsification", result["test_plan"][0])

    def test_claim_profile_round_trips_in_portable_bundle(self):
        node = self.store.add_node(self.problem["id"], "assumption", "Portable claim",
                                   assumptions=["A"], uncertainty="U", falsifier="F")
        imported = self.store.import_problem(self.store.export_problem(self.problem["id"]))
        copied = self.store.graph(imported["problem_id"])["nodes"]
        match = next(item for item in copied if item["statement"] == node["statement"])
        self.assertEqual((["A"], "U", "F"),
                         (match["assumptions"], match["uncertainty"], match["falsifier"]))

    def test_noop_update_does_not_pollute_audit_log(self):
        before = len(self.store.list_audit_events(self.problem["id"]))
        self.store.update_node(self.goal["id"], statement=self.goal["statement"],
                               confidence=self.goal["confidence"], status=self.goal["status"])
        self.assertEqual(before, len(self.store.list_audit_events(self.problem["id"])))

    def test_audit_log_records_ordered_mutations_and_survives_problem_delete(self):
        updated = self.store.update_problem(self.problem["id"], title="Launch revised")
        edge_id = self.store.graph(self.problem["id"])["edges"][0]["id"]
        self.store.delete_edge(edge_id)
        self.store.delete_node(self.unknown["id"])
        self.store.delete_problem(self.problem["id"])
        events = self.store.list_audit_events(self.problem["id"])
        self.assertEqual(sorted(event["sequence"] for event in events), [event["sequence"] for event in events])
        self.assertEqual("deleted", events[-1]["action"])
        self.assertEqual("problem", events[-1]["entity_type"])
        self.assertEqual("Launch revised", events[-1]["payload"]["title"])

    def test_evidence_contract_normalizes_legacy_records(self):
        record = normalize_evidence(["old-note"])[0]
        self.assertEqual("legacy", record["verification_status"])
        self.assertEqual(0.15, evidence_strength([record]))

    def test_evidence_contract_rejects_bad_reliability(self):
        with self.assertRaisesRegex(ValueError, "reliability"):
            normalize_evidence([{"source": "x", "reliability": 2}])

    def test_reproduced_evidence_is_stronger_than_unverified(self):
        weak = normalize_evidence([{"source": "x", "reliability": 0.9}])
        strong = normalize_evidence([{"source": "x", "reliability": 0.9, "verification_status": "reproduced"}])
        self.assertGreater(evidence_strength(strong), evidence_strength(weak))

    def test_break_it_reference_benchmark_passes(self):
        result = run_ranking_benchmark()
        self.assertTrue(result["gate_passed"])
        self.assertEqual(1.0, result["metrics"]["top1_accuracy"])

    def test_taxonomy_reference_benchmark_covers_three_domains(self):
        result = run_taxonomy_benchmark()
        self.assertTrue(result["gate_passed"])
        self.assertEqual(12, result["metrics"]["cases"])
        self.assertEqual(["incident", "product", "science"], result["metrics"]["domains"])

    def test_end_to_end_operation_contract_passes(self):
        result = run_operation_benchmark()
        self.assertTrue(result["passed"])
        self.assertEqual({"passed": 5, "total": 5}, result["summary"])

    def test_break_it_sensitivity_is_robust_across_profiles(self):
        result = run_sensitivity_benchmark()
        self.assertTrue(result["gate_passed"])
        self.assertEqual({"cases": 3, "profiles": 4, "robust_case_rate": 1.0}, result["metrics"])

    def test_invalid_scoring_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "weights"):
            ScoringProfile("invalid", -1, 0, 0)

    def test_break_it_discloses_scoring_profile(self):
        result = self.engine.break_it()
        self.assertEqual("balanced-v1", result["scoring_profile"]["name"])

    def test_why_reports_direct_contradiction_as_challenge(self):
        counter = self.store.add_node(self.problem["id"], "fact", "Counterexample", 0.9, ["observed"])
        self.store.add_edge(self.problem["id"], counter["id"], self.goal["id"], "contradicts")
        result = Engine(self.store.graph(self.problem["id"])).why(self.goal["id"])
        self.assertEqual([counter["id"]], [node["id"] for node in result["challenges"]])

    def test_v03_support_edges_migrate_to_intuitive_direction(self):
        path = Path(self.tmp.name) / "supports-v3.db"
        old = Store(path)
        p = old.create_problem("Old semantics", "migration")
        claim = old.add_node(p["id"], "assumption", "Claim")
        fact = old.add_node(p["id"], "fact", "Evidence", evidence=["source"])
        # Recreate the V0.3 direction and version marker directly.
        with old.connect() as db:
            db.execute("INSERT INTO edges(id,problem_id,source_id,target_id,type) VALUES('old-edge',?,?,?,'supports')",
                       (p["id"], claim["id"], fact["id"]))
            db.execute("UPDATE schema_meta SET value='3' WHERE key='schema_version'")
        migrated = Store(path).graph(p["id"])
        edge = migrated["edges"][0]
        self.assertEqual((fact["id"], claim["id"]), (edge["source_id"], edge["target_id"]))

    def test_invalid_functional_role_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not valid"):
            self.store.add_node(self.problem["id"], "fact", "A question is not a fact role", role="question")

    def test_v02_database_migrates_role_column_without_data_loss(self):
        legacy_path = Path(self.tmp.name) / "legacy.db"
        db = sqlite3.connect(legacy_path)
        try:
            db.executescript("""
                CREATE TABLE problems(id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,created_at TEXT);
                CREATE TABLE nodes(id TEXT PRIMARY KEY,problem_id TEXT NOT NULL,type TEXT NOT NULL,statement TEXT NOT NULL,
                    confidence REAL NOT NULL,evidence TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT);
                CREATE TABLE edges(id TEXT PRIMARY KEY,problem_id TEXT NOT NULL,source_id TEXT NOT NULL,target_id TEXT NOT NULL,
                    type TEXT NOT NULL,created_at TEXT);
                INSERT INTO problems VALUES('p','Legacy','old','then');
                INSERT INTO nodes VALUES('n','p','assumption','Old claim',0.4,'[]','open','then');
            """)
            db.commit()
        finally:
            db.close()
        migrated = Store(legacy_path).get_node("n")
        self.assertEqual("hypothesis", migrated["role"])
        self.assertEqual("Old claim", migrated["statement"])

    def test_validation_rejects_fact_without_evidence(self):
        unsupported = self.store.add_node(self.problem["id"], "fact", "Unsupported claim", 0.7)
        result = Engine(self.store.graph(self.problem["id"])).validate()
        self.assertFalse(result["valid"])
        self.assertIn(unsupported["id"], [i["node_id"] for i in result["issues"]])


if __name__ == "__main__":
    unittest.main()
