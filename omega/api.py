from __future__ import annotations

import argparse
import json
import mimetypes
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .engine import Engine
from .store import Store
from . import __version__
from .report import analyze_spec, evaluator_session
from .spec import run_spec
from .mission_control import (create_mission, execute_mission, list_missions,
                              load_mission, route_operator_command, verify_mission,
                              zero_challenge)
from .cyber_expert import answer_request, cyber_status, freeze_final_exam, run_bounded_assessment
from .cyber_external_evaluation import external_evaluation_status, freeze_external_evaluation_packet
from .cyber_promotion import promotion_status, run_promotion_campaign
from .public_gateway import gateway_scan, gateway_status, initialize_gateway, release_readiness, run_public_gateway_mission

WEB_ROOT = Path(__file__).with_name("web")


def make_handler(store: Store):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path) -> None:
            body = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                content_type += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:
            request_path = urlparse(self.path).path
            if request_path in {"/", "/index.html"}:
                return self._send_file(WEB_ROOT / "index.html")
            if request_path in {"/app.js", "/styles.css", "/onboarding.css"}:
                return self._send_file(WEB_ROOT / request_path[1:])
            parts = request_path.strip("/").split("/")
            try:
                if parts == ["health"]:
                    return self._send(200, {"status": "ok", "version": __version__})
                if parts == ["problems"]:
                    return self._send(200, {"problems": store.list_problems()})
                if parts == ["evaluations"]:
                    return self._send(200, {"evaluations": store.list_evaluations()})
                if parts == ["missions"]:
                    return self._send(200, {"missions": list_missions(Path.cwd())})
                if len(parts) == 2 and parts[0] == "missions":
                    return self._send(200, asdict(load_mission(Path.cwd(), parts[1])))
                if parts == ["cyber", "status"] or parts == ["api", "cyber", "status"]:
                    return self._send(200, cyber_status(Path.cwd()))
                if parts == ["cyber", "training"] or parts == ["api", "cyber", "training"]:
                    return self._send(200, cyber_status(Path.cwd()))
                if parts == ["cyber", "promotion-status"] or parts == ["api", "cyber", "promotion-status"]:
                    return self._send(200, promotion_status(Path.cwd()))
                if parts == ["cyber", "external-evaluation"] or parts == ["api", "cyber", "external-evaluation"]:
                    return self._send(200, external_evaluation_status(Path.cwd()))
                if parts == ["public-gateway", "status"] or parts == ["api", "public-gateway", "status"]:
                    return self._send(200, gateway_status(Path.cwd()))
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "graph":
                    return self._send(200, store.graph(parts[1]))
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "export":
                    return self._send(200, store.export_problem(parts[1]))
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "audit":
                    return self._send(200, {"events": store.list_audit_events(parts[1])})
                self._send(404, {"error": "route not found"})
            except KeyError as exc:
                self._send(404, {"error": str(exc)})

        def do_POST(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                data = self._body()
                if parts == ["problems"]:
                    return self._send(201, store.create_problem(data["title"], data.get("description", "")))
                if parts == ["imports"]:
                    return self._send(201, store.import_problem(data))
                if parts == ["evaluations"]:
                    return self._send(201, store.record_evaluation(data))
                if parts == ["console"]:
                    return self._send(200, route_operator_command(Path.cwd(), data.get("command", "")))
                if parts == ["missions"]:
                    return self._send(201, asdict(create_mission(Path.cwd(), data["objective"])))
                if len(parts) == 3 and parts[0] == "missions" and parts[2] == "challenge":
                    return self._send(200, asdict(zero_challenge(Path.cwd(), parts[1])))
                if len(parts) == 3 and parts[0] == "missions" and parts[2] == "execute":
                    return self._send(200, execute_mission(Path.cwd(), parts[1]))
                if len(parts) == 3 and parts[0] == "missions" and parts[2] == "verify":
                    return self._send(200, asdict(verify_mission(Path.cwd(), parts[1], evidence_ref=data.get("evidence_ref"))))
                if parts == ["cyber", "request"] or parts == ["api", "cyber", "request"]:
                    return self._send(200, answer_request(Path.cwd(), data.get("request", ""),
                                                          environment=data.get("environment", "READ_ONLY_ANALYSIS"),
                                                          authorization=data.get("authorization")))
                if parts == ["cyber", "train"] or parts == ["api", "cyber", "train"]:
                    return self._send(200, run_bounded_assessment(Path.cwd()))
                if parts == ["cyber", "mastery"] or parts == ["api", "cyber", "mastery"]:
                    return self._send(200, freeze_final_exam(Path.cwd()))
                if parts == ["cyber", "research-eval"] or parts == ["api", "cyber", "research-eval"]:
                    return self._send(200, run_promotion_campaign(Path.cwd()))
                if parts == ["cyber", "external-evaluation", "freeze"] or parts == ["api", "cyber", "external-evaluation", "freeze"]:
                    return self._send(200, freeze_external_evaluation_packet(Path.cwd()))
                if parts == ["public-gateway", "init"] or parts == ["api", "public-gateway", "init"]:
                    return self._send(200, initialize_gateway(Path.cwd()))
                if parts == ["public-gateway", "scan"] or parts == ["api", "public-gateway", "scan"]:
                    return self._send(200, gateway_scan(Path.cwd(), data.get("target", "")))
                if parts == ["public-gateway", "readiness"] or parts == ["api", "public-gateway", "readiness"]:
                    return self._send(200, release_readiness(Path.cwd()))
                if parts == ["public-gateway", "mission-run"] or parts == ["api", "public-gateway", "mission-run"]:
                    return self._send(200, run_public_gateway_mission(Path.cwd()))
                if parts == ["specs", "analyze"]:
                    return self._send(201, analyze_spec(store, data))
                if parts == ["examples", "launch"]:
                    example = json.loads((Path(__file__).parent.parent / "examples" / "launch.problem.json").read_text(encoding="utf-8"))
                    return self._send(201, run_spec(store, example)["imported"])
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "nodes":
                    return self._send(201, store.add_node(parts[1], data["type"], data["statement"],
                                                           data.get("confidence", 0.5), data.get("evidence"), data.get("role"),
                                                           data.get("assumptions"), data.get("uncertainty", ""),
                                                           data.get("falsifier", "")))
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
                if len(parts) == 3 and parts[0] == "problems" and parts[2] == "evaluator-session":
                    return self._send(201, evaluator_session(store, parts[1], data["node_id"]))
                self._send(404, {"error": "route not found"})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def do_DELETE(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                if len(parts) == 2 and parts[0] == "problems":
                    return self._send(200, store.delete_problem(parts[1]))
                if len(parts) == 2 and parts[0] == "nodes":
                    return self._send(200, store.delete_node(parts[1]))
                if len(parts) == 2 and parts[0] == "edges":
                    return self._send(200, store.delete_edge(parts[1]))
                self._send(404, {"error": "route not found"})
            except KeyError as exc:
                self._send(404, {"error": str(exc)})

        def do_PATCH(self) -> None:
            parts = urlparse(self.path).path.strip("/").split("/")
            try:
                data = self._body()
                if len(parts) == 2 and parts[0] == "problems":
                    allowed = {key: data[key] for key in ("title", "description") if key in data}
                    return self._send(200, store.update_problem(parts[1], **allowed))
                if len(parts) == 2 and parts[0] == "nodes":
                    allowed = {("kind" if key == "type" else key): data[key] for key in ("type", "statement", "confidence", "evidence", "status", "role",
                                                          "assumptions", "uncertainty", "falsifier") if key in data}
                    return self._send(200, store.update_node(parts[1], **allowed))
                self._send(404, {"error": "route not found"})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[omega] {fmt % args}")
    return Handler


def run(host: str = "127.0.0.1", port: int = 8787, db: str = "data/omega.db") -> None:
    server = ThreadingHTTPServer((host, port), make_handler(Store(db)))
    print(f"OMEGA {__version__} listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="data/omega.db")
    args = parser.parse_args(); run(args.host, args.port, args.db)
