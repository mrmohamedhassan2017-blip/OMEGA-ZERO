import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from omega.api import make_handler
from omega.store import Store


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


if __name__ == "__main__":
    unittest.main()
