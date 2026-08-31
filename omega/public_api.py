"""Public-only HTTP surface for the OMEGA Public Gateway safe backend.

This module intentionally exposes only:

- GET /public/health
- POST /public/code-scan

It does not mount the local OMEGA operator UI, Supervisor, Wake Plane,
Task Continuity, private evidence, shell, filesystem, or internal API routes.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .public_backend import public_code_scan, public_health

MAX_REQUEST_BYTES = 16_384
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8787


def _allowed_origins() -> set[str]:
    raw = os.environ.get("PUBLIC_FRONTEND_ORIGIN", "").strip()
    if not raw:
        return set()
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def _safe_json_error(message: str, *, code: str) -> dict[str, str]:
    return {"error": message, "error_code": code}


def make_public_handler():
    allowed_origins = _allowed_origins()

    class PublicHandler(BaseHTTPRequestHandler):
        server_version = "OMEGA-PublicGateway/1"
        sys_version = ""

        def _origin_allowed(self) -> str | None:
            origin = (self.headers.get("Origin") or "").strip().rstrip("/")
            if origin and origin in allowed_origins:
                return origin
            return None

        def _send_json(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            origin = self._origin_allowed()
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> tuple[dict, str | None]:
            length_text = self.headers.get("Content-Length", "0")
            try:
                length = int(length_text)
            except ValueError:
                return {}, "INVALID_CONTENT_LENGTH"
            if length < 0 or length > MAX_REQUEST_BYTES:
                return {}, "REQUEST_TOO_LARGE"
            try:
                raw = self.rfile.read(length) if length else b"{}"
                parsed = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return {}, "INVALID_JSON"
            if not isinstance(parsed, dict):
                return {}, "INVALID_JSON_OBJECT"
            return parsed, None

        def do_OPTIONS(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/public/health", "/public/code-scan"}:
                return self._send_json(404, _safe_json_error("route not found", code="NOT_FOUND"))
            self._send_json(204, {})

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/public/health":
                health = dict(public_health())
                health["deployment"] = os.environ.get("PUBLIC_DEPLOYMENT_CLASSIFICATION", "PUBLIC_SAFE_BACKEND")
                health["public_routes"] = ["GET /public/health", "POST /public/code-scan"]
                return self._send_json(200, health)
            return self._send_json(404, _safe_json_error("route not found", code="NOT_FOUND"))

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/public/code-scan":
                return self._send_json(404, _safe_json_error("route not found", code="NOT_FOUND"))
            data, error = self._read_body()
            if error:
                status = 413 if error == "REQUEST_TOO_LARGE" else 400
                return self._send_json(status, _safe_json_error("invalid request", code=error))
            client_id = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
            return self._send_json(200, public_code_scan(str(data.get("target", "")), client_id=client_id))

        def log_message(self, fmt: str, *args: object) -> None:
            # Privacy-safe operational log: method/path/status class only; no request body.
            print(f"[omega-public] {self.command} {urlparse(self.path).path} {fmt % args}")

    return PublicHandler


def run(host: str = DEFAULT_HOST, port: int | None = None) -> None:
    actual_port = port or int(os.environ.get("PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, actual_port), make_public_handler())
    print(f"OMEGA Public Gateway listening on http://{host}:{actual_port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the public-only OMEGA Public Gateway backend.")
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args(argv)
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
