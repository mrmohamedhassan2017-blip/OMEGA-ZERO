from __future__ import annotations

import http.client
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from omega.public_api import MAX_REQUEST_BYTES, make_public_handler


class PublicApiTests(unittest.TestCase):
    def start_server(self, *, origin: str | None = None):
        env = {}
        if origin:
            env["PUBLIC_FRONTEND_ORIGIN"] = origin
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_public_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def request(self, server, method: str, path: str, body: dict | bytes | None = None, *, origin: str | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        headers = {}
        payload: bytes | None = None
        if origin:
            headers["Origin"] = origin
        if isinstance(body, dict):
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif isinstance(body, bytes):
            payload = body
            headers["Content-Type"] = "application/json"
        conn.request(method, path, payload, headers)
        response = conn.getresponse()
        raw = response.read()
        conn.close()
        parsed = json.loads(raw or b"{}")
        return response.status, dict(response.getheaders()), parsed

    def test_exposes_only_public_health_and_code_scan(self):
        server = self.start_server()
        status, _, health = self.request(server, "GET", "/public/health")
        self.assertEqual(200, status)
        self.assertEqual(["GET /public/health", "POST /public/code-scan"], health["public_routes"])
        self.assertNotIn("pid", json.dumps(health).lower())
        self.assertNotIn("c:\\", json.dumps(health).lower())

        status, _, scan = self.request(server, "POST", "/public/code-scan", {"target": "fixture:known-good"})
        self.assertEqual(200, status)
        self.assertEqual("VERIFIED_CLEAN_WITHIN_CHECKS", scan["zero_verdict"])

        for method, path in (("GET", "/health"), ("GET", "/problems"), ("POST", "/console")):
            status, _, body = self.request(server, method, path, {} if method == "POST" else None)
            self.assertEqual(404, status)
            self.assertEqual("NOT_FOUND", body["error_code"])

    def test_invalid_and_ssrf_inputs_are_sanitized(self):
        server = self.start_server()
        status, _, invalid = self.request(server, "POST", "/public/code-scan", {"target": "not-a-url"})
        self.assertEqual(200, status)
        self.assertEqual("INVALID_INPUT", invalid["zero_verdict"])
        self.assertNotIn("Traceback", json.dumps(invalid))

        status, _, ssrf = self.request(server, "POST", "/public/code-scan", {"target": "http://169.254.169.254/latest/meta-data"})
        self.assertEqual(200, status)
        self.assertEqual("INVALID_INPUT", ssrf["zero_verdict"])
        self.assertNotIn("Traceback", json.dumps(ssrf))

    def test_request_size_is_bounded(self):
        server = self.start_server()
        oversized = b'{"target":"' + (b"x" * (MAX_REQUEST_BYTES + 1)) + b'"}'
        status, _, body = self.request(server, "POST", "/public/code-scan", oversized)
        self.assertEqual(413, status)
        self.assertEqual("REQUEST_TOO_LARGE", body["error_code"])

    def test_cors_is_exact_origin_only(self):
        allowed = "https://example-public-gateway.test"
        server = self.start_server(origin=allowed)

        status, headers, _ = self.request(server, "OPTIONS", "/public/code-scan", origin=allowed)
        self.assertEqual(204, status)
        self.assertEqual(allowed, headers.get("Access-Control-Allow-Origin"))

        status, headers, _ = self.request(server, "OPTIONS", "/public/code-scan", origin="https://evil.example")
        self.assertEqual(204, status)
        self.assertNotIn("Access-Control-Allow-Origin", headers)


if __name__ == "__main__":
    unittest.main()
