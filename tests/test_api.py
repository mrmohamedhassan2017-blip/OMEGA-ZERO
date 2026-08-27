import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from omega.api import make_handler
from omega.store import Store
from omega.evaluation import prepare_blind_case, run_blind_case, score_reveal


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "api.db")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()

    def request(self, method, path, payload=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        body = json.dumps(payload).encode() if payload is not None else None
        conn.request(method, path, body, {"Content-Type": "application/json"} if body else {})
        response = conn.getresponse(); data = json.loads(response.read()); conn.close()
        return response.status, data

    def test_full_problem_graph_and_analysis_flow(self):
        status, problem = self.request("POST", "/problems", {"title": "API flow", "description": "test"})
        self.assertEqual(201, status)
        _, goal = self.request("POST", f"/problems/{problem['id']}/nodes",
                               {"type": "assumption", "statement": "It works", "confidence": 0.4})
        _, unknown = self.request("POST", f"/problems/{problem['id']}/nodes",
                                  {"type": "unknown", "statement": "Demand?", "confidence": 0.2})
        status, _ = self.request("POST", f"/problems/{problem['id']}/edges",
                                 {"source_id": goal["id"], "target_id": unknown["id"], "type": "depends_on"})
        self.assertEqual(201, status)
        status, why = self.request("POST", f"/problems/{problem['id']}/actions/why", {"node_id": goal["id"]})
        self.assertEqual(200, status); self.assertEqual(unknown["id"], why["unresolved_gaps"][0]["id"])
        status, updated = self.request("PATCH", f"/nodes/{unknown['id']}", {"status": "resolved", "confidence": 0.8})
        self.assertEqual(200, status); self.assertEqual("resolved", updated["status"])

    def test_bad_input_returns_json_error(self):
        status, data = self.request("POST", "/problems", {})
        self.assertEqual(400, status); self.assertIn("error", data)

    def test_evaluation_recording_routes(self):
        problem = self.store.create_problem("Eval", "API")
        self.store.add_node(problem["id"], "unknown", "Weak", 0.1)
        self.store.add_node(problem["id"], "assumption", "Strong", 0.8)
        bundle = self.store.export_problem(problem["id"])
        keys = [n["key"] for n in bundle["payload"]["nodes"]]
        prepared = prepare_blind_case(bundle, {"expected_order": keys, "evaluator_ref": "api"}, salt="api-salt")
        record = score_reveal(prepared["public_case"], run_blind_case(prepared["public_case"]), prepared["private_reveal"])
        status, _ = self.request("POST", "/evaluations", record)
        self.assertEqual(201, status)
        status, payload = self.request("GET", "/evaluations")
        self.assertEqual(200, status); self.assertEqual(1, len(payload["evaluations"]))

    def test_invalid_evidence_is_rejected_over_http(self):
        _, problem = self.request("POST", "/problems", {"title": "Evidence", "description": "test"})
        status, data = self.request("POST", f"/problems/{problem['id']}/nodes",
                                    {"type": "fact", "statement": "Claim", "evidence": [{"reliability": 2}]})
        self.assertEqual(400, status); self.assertIn("evidence.source", data["error"])

    def test_invalid_type_role_pair_is_rejected_over_http(self):
        _, problem = self.request("POST", "/problems", {"title": "Role", "description": "test"})
        status, data = self.request("POST", f"/problems/{problem['id']}/nodes",
                                    {"type": "constraint", "role": "prediction", "statement": "Mismatch"})
        self.assertEqual(400, status); self.assertIn("not valid", data["error"])

    def test_export_import_delete_lifecycle(self):
        _, problem = self.request("POST", "/problems", {"title": "Portable API", "description": "test"})
        _, node = self.request("POST", f"/problems/{problem['id']}/nodes",
                               {"type": "unknown", "role": "question", "statement": "Will it round-trip?"})
        status, bundle = self.request("GET", f"/problems/{problem['id']}/export")
        self.assertEqual(200, status); self.assertIn("sha256", bundle)
        status, imported = self.request("POST", "/imports", bundle)
        self.assertEqual(201, status); self.assertEqual(1, imported["nodes_imported"])
        status, deleted = self.request("DELETE", f"/problems/{problem['id']}")
        self.assertEqual(200, status); self.assertEqual(1, deleted["nodes_deleted"])
        status, _ = self.request("GET", f"/problems/{problem['id']}/graph")
        self.assertEqual(404, status)

    def test_update_delete_and_audit_lifecycle(self):
        _, problem = self.request("POST", "/problems", {"title": "Audit API", "description": "before"})
        _, left = self.request("POST", f"/problems/{problem['id']}/nodes",
                               {"type": "assumption", "statement": "Left"})
        _, right = self.request("POST", f"/problems/{problem['id']}/nodes",
                                {"type": "unknown", "statement": "Right"})
        _, edge = self.request("POST", f"/problems/{problem['id']}/edges",
                               {"source_id": left["id"], "target_id": right["id"], "type": "depends_on"})
        status, updated = self.request("PATCH", f"/problems/{problem['id']}", {"description": "after"})
        self.assertEqual(200, status); self.assertEqual("after", updated["description"])
        self.assertEqual(200, self.request("DELETE", f"/edges/{edge['id']}")[0])
        self.assertEqual(200, self.request("DELETE", f"/nodes/{right['id']}")[0])
        status, audit = self.request("GET", f"/problems/{problem['id']}/audit")
        self.assertEqual(200, status)
        self.assertEqual(["created", "created", "created", "created", "updated", "deleted", "deleted"],
                         [event["action"] for event in audit["events"]])

    def test_declarative_spec_analysis_endpoint(self):
        spec = json.loads((Path(__file__).parents[1] / "examples" / "launch.problem.json").read_text(encoding="utf-8"))
        status, report = self.request("POST", "/specs/analyze", spec)
        self.assertEqual(201, status); self.assertTrue(report["validation"]["valid"])
        self.assertEqual("launch", report["analysis_target"]["key"])


if __name__ == "__main__":
    unittest.main()
