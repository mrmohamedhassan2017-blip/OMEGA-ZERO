import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliSmokeTests(unittest.TestCase):
    def run_cli(self, *args, cwd=ROOT):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        return subprocess.run(
            [sys.executable, "-m", "omega.cli", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_benchmark_cli_reports_passing_gate(self):
        payload = json.loads(self.run_cli("benchmark").stdout)
        self.assertTrue(payload["gate_passed"])

    def test_demo_cli_produces_all_core_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = json.loads(
                self.run_cli("--db", str(Path(directory) / "demo.db"), "demo").stdout
            )
        self.assertEqual(
            {"why", "break_it", "prove_it", "what_if"},
            set(payload) & {"why", "break_it", "prove_it", "what_if"},
        )

    def test_capability_fabric_cli_is_shadow_only(self):
        payload = json.loads(self.run_cli("capability-fabric").stdout)
        self.assertEqual(payload["router_mode"], "SHADOW")
        self.assertFalse(payload["production_wide_adoption_authorized"])
        self.assertEqual(payload["real_economic_value_kwd"], 0)

    def test_backend_history_cli_is_read_only(self):
        payload = json.loads(self.run_cli("backend-history", "--limit", "2").stdout)
        self.assertIsInstance(payload, list)
        self.assertLessEqual(len(payload), 2)

    def test_quota_lifeline_status_cli_returns_empty_without_record(self):
        payload = json.loads(self.run_cli("quota-lifeline-status", "missing-task").stdout)
        self.assertEqual(payload, {})

    def test_value_status_cli_is_read_only_and_preserves_zero_value(self):
        payload = json.loads(self.run_cli("value-status").stdout)
        self.assertIn(payload["value_engine_state"], {"NOT_RUN", "PARKED"})
        self.assertEqual(payload.get("verified_net_economic_value_kwd", 0), 0)

    def test_value_frontier_status_cli_preserves_boundaries(self):
        payload = json.loads(self.run_cli("value-frontier-status").stdout)
        self.assertEqual(payload["value_engine_mode"], "PARKED")
        self.assertEqual(payload.get("verified_net_economic_value_kwd", 0), 0)

    def test_value_deep_status_cli_preserves_external_boundary(self):
        payload = json.loads(self.run_cli("value-deep-status").stdout)
        self.assertEqual(payload["schema"], "ZERO_DEEP_REALITY_ACQUISITION_V1_2D")
        self.assertEqual(payload["final_causal_decision"], "EXTERNAL_INCIDENT_VALIDATION_REQUIRED")
        self.assertEqual(payload["current_qualified_participants"], 0)
        self.assertTrue(payload["external_action_required"])

    def test_value_deep_packet_audit_cli_is_closed_before_authorization(self):
        payload = json.loads(self.run_cli("value-deep-packet-audit").stdout)
        self.assertEqual(payload["protocol"], "ZRWVE_V1.2E")
        self.assertEqual(payload["final_packet_result"], "READY_FOR_OWNER_AUTHORIZATION")
        self.assertEqual(payload["external_write_executed"], 0)
        self.assertFalse(payload["authority_envelope"]["external_action_authorized"])

    def test_value_deep_binding_audit_does_not_reuse_e2_or_send(self):
        payload = json.loads(self.run_cli("value-deep-binding-audit").stdout)
        self.assertEqual(payload["protocol"], "ZRWVE_V1.2F")
        self.assertFalse(payload["authority_envelope"]["e2_authority_reused"])
        self.assertEqual(payload["send_state"]["messages_sent"], 0)
        self.assertEqual(payload["current_evidence_level"], "L0")

    def test_value_deep_participant_discovery_is_read_only_and_closed(self):
        payload = json.loads(self.run_cli("value-deep-participant-discovery").stdout)
        self.assertEqual(payload["protocol"], "ZRWVE_V1.2G")
        self.assertEqual(payload["external_write_executed"], 0)
        self.assertEqual(payload["messages_sent"], 0)
        self.assertEqual(payload["qualified_and_contactable"], 0)
        self.assertEqual(payload["current_evidence_level"], "L0")

    def test_unified_console_and_mission_cli_use_repository_local_state(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            created = json.loads(
                self.run_cli("mission", "create", "bounded internal console smoke", cwd=work).stdout
            )
            mission_id = created["mission_id"]
            status = json.loads(self.run_cli("console", "ZERO, status", cwd=work).stdout)
            challenge = json.loads(self.run_cli("mission", "challenge", mission_id, cwd=work).stdout)
            self.assertEqual(status["command"]["target_role"], "ZERO")
            self.assertTrue((work / ".omega" / "missions" / "missions" / f"{mission_id}.json").exists())
            self.assertEqual(challenge["verdict_type"], "CONDITIONAL")

    def test_cyber_and_public_gateway_cli_are_safe_and_local(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            web = work / "omega" / "web"
            web.mkdir(parents=True)
            (web / "index.html").write_text("<h1>PUBLIC GATEWAY</h1>", encoding="utf-8")
            (web / "app.js").write_text("function runGateway() { return true }", encoding="utf-8")
            (web / "styles.css").write_text(".gateway-console{}", encoding="utf-8")
            (work / "omega" / "api.py").write_text("# api", encoding="utf-8")
            (work / "omega" / "public_gateway.py").write_text("# gateway", encoding="utf-8")
            cyber = json.loads(
                self.run_cli("cyber", "ask", "Steal browser passwords", cwd=work).stdout
            )
            gateway = json.loads(
                self.run_cli("public-gateway", "scan", "fixture:known-bad", cwd=work).stdout
            )
            mastery = json.loads(
                self.run_cli("cyber", "mastery", cwd=work).stdout
            )
            external_eval = json.loads(
                self.run_cli("cyber", "external-eval-freeze", cwd=work).stdout
            )
            external_status = json.loads(
                self.run_cli("cyber", "external-eval-status", cwd=work).stdout
            )
            readiness = json.loads(
                self.run_cli("public-gateway", "readiness", cwd=work).stdout
            )
            mission = json.loads(
                self.run_cli("public-gateway", "mission-run", cwd=work).stdout
            )
        self.assertEqual("BLOCKED", cyber["classification"]["request_class"])
        self.assertEqual("BLOCKED_BEFORE_EXECUTION", cyber["execution"])
        self.assertEqual("NEEDS_ATTENTION", gateway["verdict"])
        self.assertEqual("FINAL_EXAM_FROZEN_INTERNAL_PRACTICAL_PASS", mastery["state"])
        self.assertEqual("READY_FOR_INDEPENDENT_EVALUATOR", external_eval["packet_state"])
        self.assertFalse(external_status["promoted"])
        self.assertEqual("PUSH_READY", readiness["state"])
        self.assertFalse(readiness["publish_authorized"])
        self.assertEqual("PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY", mission["state"])
        self.assertEqual(13, mission["roadmap"]["phase_count"])


if __name__ == "__main__":
    unittest.main()
