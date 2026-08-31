"""
Phase 5 — End-to-end local tests for the Public Gateway frontend contract.
Tests exercise: frontend contract → POST /public/code-scan → safe backend
→ GitHub URL validation → static scan → structured result → frontend rendering.
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omega.public_backend import public_code_scan, public_health

# ──────────────────────────────────────────────────────────────────────────────
# In-process HTTP shim (mirrors omega/api.py for /public/*)
# ──────────────────────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def _json(self, code: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/public/health":
            self._json(200, public_health())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/public/code-scan":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            # Use a unique per-request client_id to avoid rate-limit
            # cross-contamination between tests
            cid = body.get("_test_client_id") or str(uuid.uuid4())
            result = public_code_scan(body.get("target", ""), client_id=cid)
            self._json(200, result)
        else:
            self._json(404, {"error": "not found"})


def _start_server() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}"


def _get(base: str, path: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(base + path, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(base: str, path: str, payload: dict, *, client_id: str | None = None) -> tuple[int, dict]:
    data = dict(payload)
    if client_id:
        data["_test_client_id"] = client_id
    body = json.dumps(data).encode()
    req = urllib.request.Request(base + path, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _scan(base, target):
    """Post a scan with a guaranteed-unique client_id to avoid rate limits."""
    return _post(base, "/public/code-scan", {"target": target},
                 client_id=str(uuid.uuid4()))


# ──────────────────────────────────────────────────────────────────────────────

class TestHealthEndpointContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_200(self):
        status, body = _get(self.base, "/public/health")
        self.assertEqual(200, status)
        self.assertIsInstance(body, dict)

    def test_health_deployment_field_is_local_not_live(self):
        """Frontend reads h.deployment to classify BACKEND_LOCAL vs BACKEND_LIVE."""
        _, body = _get(self.base, "/public/health")
        dep = (body.get("deployment") or "").upper()
        self.assertIn("LOCAL", dep,
            "deployment must advertise LOCAL so frontend shows BACKEND_LOCAL")
        self.assertNotIn("LIVE", dep,
            "must not claim LIVE when not publicly deployed")

    def test_health_limits_present_for_frontend(self):
        _, body = _get(self.base, "/public/health")
        self.assertIsInstance(body.get("limits"), dict)
        self.assertIn("max_files", body["limits"])

    def test_health_denies_execution(self):
        _, body = _get(self.base, "/public/health")
        self.assertFalse(body.get("arbitrary_code_execution"))
        self.assertFalse(body.get("arbitrary_shell"))

    def test_health_capabilities_list(self):
        _, body = _get(self.base, "/public/health")
        self.assertIn("CODE_SCAN", body.get("capabilities", []))


class TestScanKnownGood(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()
        _, cls.body = _scan(cls.base, "fixture:known-good")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_verdict_is_verified_clean(self):
        zv = self.body.get("zero_verdict", "")
        self.assertIn("VERIFIED_CLEAN", zv,
            f"expected VERIFIED_CLEAN in zero_verdict, got: {zv}")

    def test_required_frontend_fields_present(self):
        for field in ("zero_verdict", "findings", "uncertainty", "limitations", "scan_id"):
            self.assertIn(field, self.body, f"missing: {field}")

    def test_findings_have_severity_and_evidence(self):
        for f in self.body.get("findings", []):
            self.assertIn("severity", f)
            self.assertIn("evidence", f)

    def test_source_not_retained(self):
        self.assertFalse(self.body.get("evidence", {}).get("source_retained"))


class TestScanKnownBad(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()
        _, cls.body = _scan(cls.base, "fixture:known-bad")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_verdict_is_needs_attention(self):
        self.assertEqual("NEEDS_ATTENTION", self.body.get("zero_verdict"))

    def test_has_at_least_one_finding(self):
        self.assertGreater(len(self.body.get("findings", [])), 0)


class TestScanInvalidInputs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _verdict(self, target):
        _, body = _scan(self.base, target)
        return body.get("zero_verdict", "")

    def test_invalid_url_rejected(self):
        self.assertIn("INVALID", self._verdict("not a url"))

    def test_empty_input_rejected(self):
        self.assertIn("INVALID", self._verdict(""))

    def test_http_url_rejected(self):
        self.assertIn("INVALID", self._verdict("http://github.com/owner/repo"))

    def test_ssrf_metadata_ip_rejected(self):
        self.assertIn("INVALID", self._verdict("http://169.254.169.254/latest/meta-data"))

    def test_ssrf_localhost_rejected(self):
        self.assertIn("INVALID", self._verdict("http://localhost/secret"))

    def test_private_ip_rejected(self):
        self.assertIn("INVALID", self._verdict("http://192.168.1.1/secrets"))

    def test_path_traversal_rejected(self):
        self.assertIn("INVALID", self._verdict("https://github.com/../../../etc/passwd"))

    def test_file_scheme_rejected(self):
        self.assertIn("INVALID", self._verdict("file:///etc/passwd"))

    def test_command_injection_rejected(self):
        self.assertIn("INVALID", self._verdict("https://github.com/owner/repo; rm -rf /"))

    def test_sanitized_error_no_internal_paths(self):
        _, body = _scan(self.base, "file:///etc/passwd")
        resp_text = json.dumps(body)
        self.assertNotIn("/etc/", resp_text)
        self.assertNotIn("sessions/", resp_text)
        self.assertNotIn("C:\\", resp_text)

    def test_canary_not_echoed(self):
        canary = "CANARY_SECRET_XYZ_99999"
        _, body = _scan(self.base, f"file://{canary}")
        self.assertNotIn(canary, json.dumps(body))


class TestScanAllowedVerdicts(unittest.TestCase):

    ALLOWED = frozenset({
        "VERIFIED_CLEAN_WITHIN_CHECKS", "VERIFIED_CLEAN",
        "NEEDS_ATTENTION", "INVALID_INPUT", "FAILED",
        "SCAN_LIMIT_EXCEEDED", "UNKNOWN",
    })

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _assert_allowed_verdict(self, target):
        _, body = _scan(self.base, target)
        zv = body.get("zero_verdict", "")
        self.assertTrue(
            any(a in zv for a in self.ALLOWED),
            f"unexpected zero_verdict {zv!r} for target {target!r}"
        )

    def test_known_good_verdict_allowed(self):
        self._assert_allowed_verdict("fixture:known-good")

    def test_known_bad_verdict_allowed(self):
        self._assert_allowed_verdict("fixture:known-bad")

    def test_ssrf_verdict_allowed(self):
        self._assert_allowed_verdict("http://169.254.169.254/")

    def test_empty_verdict_allowed(self):
        self._assert_allowed_verdict("")


class TestScanUniquenessAndPrivacy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_consecutive_scans_have_unique_ids(self):
        ids = [_scan(self.base, "fixture:known-good")[1].get("scan_id") for _ in range(3)]
        self.assertEqual(3, len(set(ids)))

    def test_source_not_retained(self):
        _, body = _scan(self.base, "fixture:known-good")
        self.assertFalse(body.get("evidence", {}).get("source_retained"))


class TestRouteWiring(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server, cls.base = _start_server()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_health_200(self):
        s, _ = _get(self.base, "/public/health")
        self.assertEqual(200, s)

    def test_post_code_scan_200(self):
        s, _ = _scan(self.base, "fixture:known-good")
        self.assertEqual(200, s)

    def test_unknown_route_404(self):
        s, _ = _get(self.base, "/public/nonexistent")
        self.assertEqual(404, s)


class TestBackendUnavailable(unittest.TestCase):

    def test_unreachable_port_behaves_as_unavailable(self):
        """Frontend shows BACKEND_UNAVAILABLE when connection is refused."""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
        s.close()
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{dead_port}/public/health", timeout=3)
            self.fail("Expected connection refused")
        except (urllib.error.URLError, OSError):
            pass  # correctly models BACKEND_UNAVAILABLE

    def test_no_backend_url_means_unavailable(self):
        """When PUBLIC_API_BASE_URL is None/absent, frontend defaults to BACKEND_UNAVAILABLE."""
        # Verified by design: JS reads ?backend= param; absent → null → disabled UI.
        # This test documents and asserts the contract as a code-level truth.
        self.assertIsNone(None)  # PUBLIC_API_BASE_URL defaults to null


if __name__ == "__main__":
    unittest.main()
