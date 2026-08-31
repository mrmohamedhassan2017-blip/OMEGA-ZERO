import tempfile
import unittest
from pathlib import Path

from omega.public_gateway import (
    classify_component,
    gateway_scan,
    gateway_status,
    generate_identity_candidates,
    initialize_gateway,
    inspect_api_exposure,
    inspect_frontend_assets,
    release_readiness,
    run_gateway_benchmark,
    run_public_gateway_mission,
    score_identities,
    test_local_deployment_architecture,
    validate_public_request,
    verify_security_boundaries,
)


class PublicGatewayTests(unittest.TestCase):
    def test_public_request_validation_is_narrow_and_safe(self):
        valid = validate_public_request("https://github.com/owner/repo")
        self.assertTrue(valid["valid"])
        self.assertEqual("CODE_SCAN", valid["mission_type"])
        self.assertFalse(validate_public_request("http://github.com/owner/repo")["valid"])
        self.assertFalse(validate_public_request("C:/Users/private/repo")["valid"])

    def test_public_private_secret_boundaries(self):
        self.assertEqual("SECRET", classify_component(".env"))
        self.assertEqual("SECRET", classify_component("oauth-client.json"))
        self.assertEqual("PRIVATE_RUNTIME", classify_component(".omega/runtime/heartbeat.json"))
        self.assertEqual("PUBLIC_SAFE", classify_component("README.md"))
        self.assertEqual("PUBLIC_WITH_REVIEW", classify_component("omega/web/index.html"))

    def test_identity_candidates_are_distinct_scored_and_preserved(self):
        candidates = generate_identity_candidates()
        result = score_identities(candidates)
        self.assertEqual(3, len(candidates))
        self.assertEqual("IDENTITY-01", result["selected_identity"])
        self.assertEqual(3, len(result["scores"]))

    def test_gateway_initializes_and_known_fixtures_return_evidence_backed_verdicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = initialize_gateway(root)
            good = gateway_scan(root, "fixture:known-good")
            bad = gateway_scan(root, "fixture:known-bad")
            status = gateway_status(root)
        self.assertEqual("PUBLIC_GATEWAY_V1_BLOCKED", state["state"])
        self.assertEqual("VERIFIED_CLEAN", good["verdict"])
        self.assertEqual("NEEDS_ATTENTION", bad["verdict"])
        self.assertEqual(2, status["scan_count"])
        self.assertEqual(0, status["external_writes"])
        self.assertFalse(status["production_routing_changed"])

    def test_security_boundaries_reject_ssrf_path_traversal_and_command_injection(self):
        security = verify_security_boundaries()
        self.assertEqual("PASS", security["state"])
        self.assertEqual("PASS", security["ssrf_boundary"])
        self.assertEqual("PASS", security["path_traversal_boundary"])
        self.assertEqual("PASS", security["command_injection_boundary"])
        rejected = [item for item in security["probes"] if not item["expected_accept"]]
        self.assertTrue(rejected)
        self.assertTrue(all(not item["accepted"] for item in rejected))

    def test_release_readiness_is_push_ready_but_not_published_or_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "omega" / "web"
            web.mkdir(parents=True)
            (web / "index.html").write_text("<h1>PUBLIC GATEWAY</h1>", encoding="utf-8")
            (web / "app.js").write_text("function runGateway() { return true }", encoding="utf-8")
            (web / "styles.css").write_text(".gateway-console{}", encoding="utf-8")
            (root / "omega" / "api.py").write_text("# api", encoding="utf-8")
            (root / "omega" / "public_gateway.py").write_text("# gateway", encoding="utf-8")
            readiness = release_readiness(root)
            status = gateway_status(root)
            frontend = inspect_frontend_assets(root)
            api = inspect_api_exposure()
            deployment = test_local_deployment_architecture(root)
        self.assertEqual("PUSH_READY", readiness["state"])
        self.assertTrue(readiness["push_ready"])
        self.assertFalse(readiness["publish_authorized"])
        self.assertEqual(0, readiness["external_writes"])
        self.assertEqual("PASS", frontend["state"])
        self.assertEqual("PASS", api["state"])
        self.assertEqual("PASS", deployment["state"])
        self.assertEqual("PUSH_READY", status["release_readiness"])
        self.assertTrue(status["push_ready"])

    def test_full_v1_mission_runs_all_phases_without_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            web = root / "omega" / "web"
            web.mkdir(parents=True)
            (web / "index.html").write_text("<h1>PUBLIC GATEWAY</h1>", encoding="utf-8")
            (web / "app.js").write_text("function runGateway() { return true }", encoding="utf-8")
            (web / "styles.css").write_text(".gateway-console{}", encoding="utf-8")
            (root / "omega" / "api.py").write_text("# api", encoding="utf-8")
            (root / "omega" / "public_gateway.py").write_text("# gateway", encoding="utf-8")
            result = run_public_gateway_mission(root)
        self.assertEqual("PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY", result["state"])
        self.assertEqual(13, result["roadmap"]["phase_count"])
        self.assertTrue(all(phase["state"] == "VERIFIED" for phase in result["phase_results"]))
        self.assertTrue(result["benchmark"]["passed"])
        self.assertFalse(result["github"]["publication_performed"])
        self.assertFalse(result["github"]["push_authorized"])
        self.assertEqual(0, result["external_writes"])

    def test_gateway_benchmark_records_known_good_bad_and_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_gateway_benchmark(Path(directory))
        self.assertTrue(result["passed"])
        self.assertEqual(1, result["true_positive"])
        self.assertEqual(1, result["true_negative"])
        self.assertEqual(0, result["false_positive"])
        self.assertEqual(0, result["false_negative"])


if __name__ == "__main__":
    unittest.main()
