from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .engine import Engine
from .store import Store
from . import __version__


def make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                if parts == ["health"]:
                    return self._send(200, {"status": "ok", "version": __version__})
                if parts == ["problems"]:
                    return self._send(200, {"problems": store.list_problems()})
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "graph":
                    return self._send(200, store.graph(parts[1]))
                self._send(404, {"error": "route not found"})
            except KeyError as exc:
                self._send(404, {"error": str(exc)})

        def do_POST(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                data = self._body()
                if parts == ["problems"]:
                    return self._send(201, store.create_problem(data["title"], data.get("description", "")))
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "nodes":
                    return self._send(201, store.add_node(parts[1], data["type"], data["statement"],
                                                           data.get("confidence", 0.5), data.get("evidence"), data.get("role")))
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "edges":
                    return self._send(201, store.add_edge(parts[1], data["source_id"], data["target_id"], data["type"]))
                if len(parts) == 4 and parts[0] == "problems" and parts[2] == "actions":
                    engine = Engine(store.graph(parts[1])); action = parts[3]
                    result = {"why": lambda: engine.why(data["node_id"]),
                              "break-it": engine.break_it,
                              "prove-it": lambda: engine.prove_it(data["node_id"]),
                              "what-if": lambda: engine.what_if(data["node_id"], data.get("value", False)),
                              "validate": engine.validate}.get(action)
                    if result:
                        return self._send(200, result())
                self._send(404, {"error": "route not found"})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def do_PATCH(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                data = self._body()
                if len(parts) == 2 and parts[0] == "nodes":
                    allowed = {key: data[key] for key in ("statement", "confidence", "evidence", "status", "role") if key in data}
                    return self._send(200, store.update_node(parts[1], **allowed))
                self._send(404, {"error": "route not found"})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[omega] {fmt % args}")
    return Handler


def run(host: str = "127.0.0.1", port: int = 8787, db: str = "data/omega.db") -> None:
    server = ThreadingHTTPServer((host, port), make_handler(Store(db)))
    print(f"OMEGA v0.1 listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="data/omega.db")
    args = parser.parse_args(); run(args.host, args.port, args.db)
