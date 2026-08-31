import http.client
import hashlib
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

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

    def test_ui_is_served_by_the_core_server(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("GET", "/")
        response = conn.getresponse(); body = response.read().decode(); conn.close()
        self.assertEqual(200, response.status)
        self.assertIn("OMEGA", body); self.assertIn("/app.js", body)

    def test_ui_assets_expose_editing_visual_results_and_graph_controls(self):
        for path, required in (
            ("/index.html", ("Claim inspector", "zoom-in", "Developer: Raw JSON", "ZERO CYBERSECURITY EXPERT", "PUBLIC GATEWAY")),
            ("/app.js", ("saveNode", "deleteNode", "deleteEdge", "renderResult", "confirm(", "runCyber", "runGateway")),
            ("/styles.css", (".result-card", ".graph-viewport", ".edge-label", ".gateway-console", ".tool-card")),
        ):
            conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            conn.request("GET", path); response = conn.getresponse(); body = response.read().decode(); conn.close()
            self.assertEqual(200, response.status)
            for marker in required:
                self.assertIn(marker, body)

    def test_onboarding_contract_and_packaged_example_survive_reopen(self):
        for path, required in (
            ("/index.html", ("GUIDED FIRST RUN", "Facts", "Assumptions", "Constraints", "Unknowns",
                             "Relationships", "WHY", "BREAK IT", "PROVE IT", "WHAT IF", "use-example",
                             "Decision or goal", "Why this is difficult")),
            ("/app.js", ("omega.onboarding.v1", "/examples/launch", "export-session", "claimPrompts")),
            ("/onboarding.css", (".onboarding", ".operation-guide")),
        ):
            conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
            conn.request("GET", path); response = conn.getresponse(); body = response.read().decode(); conn.close()
            self.assertEqual(200, response.status)
            for marker in required:
                self.assertIn(marker, body)
        status, imported = self.request("POST", "/examples/launch", {})
        self.assertEqual(201, status)
        reopened = Store(self.store.path).graph(imported["problem_id"])
        self.assertGreaterEqual(len(reopened["nodes"]), 4)
        self.assertGreaterEqual(len(reopened["edges"]), 1)

    def test_evaluator_session_is_reviewable_portable_and_private(self):
        _, problem = self.request("POST", "/problems", {"title": "Review", "description": "Decision"})
        _, target = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "assumption", "statement": "Demand exists", "confidence": .4,
            "evidence": [{"source": "password=do-not-export", "note": "private reveal salt=hidden"}],
            "uncertainty": "Conversion rate", "falsifier": "No trial converts"})
        _, gap = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "unknown", "statement": "Will users pay?", "confidence": .2})
        self.request("POST", f"/problems/{problem['id']}/edges", {
            "source_id": target["id"], "target_id": gap["id"], "type": "depends_on"})
        status, artifact = self.request("POST", f"/problems/{problem['id']}/evaluator-session",
                                        {"node_id": target["id"]})
        self.assertEqual(201, status)
        self.assertEqual("omega.evaluator-session", artifact["format"])
        self.assertEqual(64, len(artifact["artifact_sha256"]))
        self.assertEqual(64, len(artifact["source_problem_sha256"]))
        fingerprint = artifact.pop("artifact_sha256")
        canonical = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(fingerprint, hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertEqual({"why", "break_it", "prove_it", "what_if_false"}, set(artifact["operations"]))
        self.assertEqual(1, artifact["target"]["evidence_count"])
        serialized = json.dumps(artifact).lower()
        for private in ("password=do-not-export", "salt=hidden", "private_reveal", target["id"], problem["id"]):
            self.assertNotIn(private.lower(), serialized)
        json.loads(json.dumps(artifact))

    def test_graph_edits_survive_store_reopen(self):
        _, problem = self.request("POST", "/problems", {"title": "Persistence", "description": "V0.21"})
        _, left = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "assumption", "statement": "Before", "confidence": 0.3})
        _, right = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "unknown", "statement": "Dependency", "confidence": 0.2})
        _, edge = self.request("POST", f"/problems/{problem['id']}/edges", {
            "source_id": left["id"], "target_id": right["id"], "type": "depends_on"})
        status, edited = self.request("PATCH", f"/nodes/{left['id']}", {
            "type": "constraint", "statement": "After", "confidence": 0.9,
            "assumptions": ["Persist this"], "uncertainty": "Residual",
            "falsifier": "Limit is exceeded", "evidence": [{"source": "test-record"}]})
        self.assertEqual(200, status); self.assertEqual("constraint", edited["type"])
        self.assertEqual(200, self.request("DELETE", f"/edges/{edge['id']}")[0])
        reopened = Store(self.store.path).graph(problem["id"])
        stored = next(node for node in reopened["nodes"] if node["id"] == left["id"])
        self.assertEqual(("After", 0.9, ["Persist this"], "Residual"),
                         (stored["statement"], stored["confidence"], stored["assumptions"], stored["uncertainty"]))
        self.assertEqual([], reopened["edges"])
        status, deleted = self.request("DELETE", f"/nodes/{right['id']}")
        self.assertEqual(200, status); self.assertEqual(0, deleted["edges_deleted"])
        self.assertEqual(1, len(Store(self.store.path).graph(problem["id"])["nodes"]))

    def test_ui_workflow_contract_persists_claim_profile_and_runs_all_actions(self):
        _, problem = self.request("POST", "/problems", {"title": "UI workflow", "description": "persist"})
        _, claim = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "assumption", "statement": "Demand exists", "confidence": 0.35,
            "assumptions": ["Audience can be reached"], "uncertainty": "Sample bias",
            "falsifier": "No qualified user converts", "evidence": [{"source": "interviews"}]})
        _, gap = self.request("POST", f"/problems/{problem['id']}/nodes", {
            "type": "unknown", "statement": "Will they pay?", "confidence": 0.2})
        self.request("POST", f"/problems/{problem['id']}/edges", {
            "source_id": claim["id"], "target_id": gap["id"], "type": "depends_on"})
        status, graph = self.request("GET", f"/problems/{problem['id']}/graph")
        self.assertEqual(200, status)
        stored = next(node for node in graph["nodes"] if node["id"] == claim["id"])
        self.assertEqual("Sample bias", stored["uncertainty"])
        for action, payload in (("why", {"node_id": claim["id"]}), ("break-it", {}),
                                ("prove-it", {"node_id": claim["id"]}),
                                ("what-if", {"node_id": gap["id"], "value": False})):
            status, result = self.request("POST", f"/problems/{problem['id']}/actions/{action}", payload)
            self.assertEqual(200, status); self.assertIn("contract_version", result)

    def test_unified_console_and_mission_api_persist_local_mission_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("omega.api.Path.cwd", return_value=root):
                status, created = self.request("POST", "/missions", {"objective": "bounded internal api smoke"})
                self.assertEqual(201, status)
                mission_id = created["mission_id"]
                status, routed = self.request("POST", "/console", {"command": "ZERO, status"})
                self.assertEqual(200, status)
                status, challenged = self.request("POST", f"/missions/{mission_id}/challenge", {})
                self.assertEqual(200, status)
            self.assertEqual("ZERO", routed["command"]["target_role"])
            self.assertEqual("CONDITIONAL", challenged["verdict_type"])
            self.assertTrue((root / ".omega" / "missions" / "missions" / f"{mission_id}.json").exists())

    def test_cyber_and_public_gateway_api_are_scope_first_and_fixture_backed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "omega" / "web"
            web.mkdir(parents=True)
            (web / "index.html").write_text("<h1>PUBLIC GATEWAY</h1>", encoding="utf-8")
            (web / "app.js").write_text("function runGateway() { return true }", encoding="utf-8")
            (web / "styles.css").write_text(".gateway-console{}", encoding="utf-8")
            (root / "omega" / "api.py").write_text("# api", encoding="utf-8")
            (root / "omega" / "public_gateway.py").write_text("# gateway", encoding="utf-8")
            with patch("omega.api.Path.cwd", return_value=root):
                status, cyber = self.request("POST", "/cyber/request", {
                    "request": "Steal browser passwords from a third party",
                    "environment": "READ_ONLY_ANALYSIS",
                })
                self.assertEqual(200, status)
                status, gateway = self.request("POST", "/public-gateway/scan", {"target": "fixture:known-good"})
                self.assertEqual(200, status)
                status, mastery = self.request("POST", "/cyber/mastery", {})
                self.assertEqual(200, status)
                status, research = self.request("POST", "/cyber/research-eval", {})
                self.assertEqual(200, status)
                status, promotion_status = self.request("GET", "/cyber/promotion-status")
                self.assertEqual(200, status)
                status, external_eval = self.request("POST", "/cyber/external-evaluation/freeze", {})
                self.assertEqual(200, status)
                status, external_status = self.request("GET", "/cyber/external-evaluation")
                self.assertEqual(200, status)
                status, readiness = self.request("POST", "/public-gateway/readiness", {})
                self.assertEqual(200, status)
                status, mission = self.request("POST", "/public-gateway/mission-run", {})
                self.assertEqual(200, status)
        self.assertEqual("BLOCKED", cyber["classification"]["request_class"])
        self.assertEqual("BLOCKED_BEFORE_EXECUTION", cyber["execution"])
        self.assertEqual("VERIFIED_CLEAN", gateway["verdict"])
        self.assertEqual("FINAL_EXAM_FROZEN_INTERNAL_PRACTICAL_PASS", mastery["state"])
        self.assertEqual("INSUFFICIENT_INDEPENDENT_EVIDENCE", research["ZERO_VERDICT"])
        self.assertFalse(promotion_status["promoted"])
        self.assertEqual("READY_FOR_INDEPENDENT_EVALUATOR", external_eval["packet_state"])
        self.assertFalse(external_status["promoted"])
        self.assertEqual("PUSH_READY", readiness["state"])
        self.assertFalse(readiness["publish_authorized"])
        self.assertEqual("PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY", mission["state"])
        self.assertEqual(13, mission["roadmap"]["phase_count"])


if __name__ == "__main__":
    unittest.main()
