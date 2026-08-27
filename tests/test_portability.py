import tempfile
import unittest
from pathlib import Path

from omega.engine import Engine
from omega.release import run_release_gates
from omega.store import Store


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = Store(self.root / "source.db")
        self.problem = self.store.create_problem("Portable", "Round trip")
        self.claim = self.store.add_node(self.problem["id"], "assumption", "Import preserves meaning", 0.5)
        self.unknown = self.store.add_node(self.problem["id"], "unknown", "What can fail?", 0.2)
        self.store.add_edge(self.problem["id"], self.claim["id"], self.unknown["id"], "depends_on")

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_is_deterministic_and_round_trips(self):
        bundle = self.store.export_problem(self.problem["id"])
        self.assertEqual(bundle, self.store.export_problem(self.problem["id"]))
        target = Store(self.root / "target.db")
        imported = target.import_problem(bundle)
        self.assertEqual(bundle, target.export_problem(imported["problem_id"]))
        self.assertTrue(Engine(target.graph(imported["problem_id"])).validate()["valid"])
        events = target.list_audit_events(imported["problem_id"])
        self.assertEqual(["imported"], [event["action"] for event in events])

    def test_tampered_bundle_is_rejected_without_partial_problem(self):
        bundle = self.store.export_problem(self.problem["id"]); bundle["payload"]["problem"]["title"] = "Tampered"
        before = len(self.store.list_problems())
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.store.import_problem(bundle)
        self.assertEqual(before, len(self.store.list_problems()))

    def test_connection_rolls_back_on_exception(self):
        with self.assertRaises(RuntimeError):
            with self.store.connect() as db:
                db.execute("INSERT INTO problems(id,title,description) VALUES('rollback','No','No')")
                raise RuntimeError("force rollback")
        with self.assertRaises(KeyError):
            self.store.get_problem("rollback")

    def test_delete_cascades_and_backup_restores(self):
        backup = self.store.backup_to(self.root / "backup.db")
        result = self.store.delete_problem(self.problem["id"])
        self.assertEqual(2, result["nodes_deleted"])
        with self.assertRaises(KeyError):
            self.store.get_node(self.claim["id"])
        restored = self.store.restore_from(backup["path"])
        self.assertEqual(1, restored["problems"])
        self.assertEqual(2, len(self.store.graph(self.problem["id"])["nodes"]))

    def test_release_gates_pass(self):
        result = run_release_gates()
        self.assertTrue(result["passed"])
        self.assertEqual({"passed": 5, "total": 5}, result["summary"])


if __name__ == "__main__":
    unittest.main()
