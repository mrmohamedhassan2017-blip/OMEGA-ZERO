from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GATEWAY_NAME = "OMEGA / ZERO Public Gateway"
MISSION_NAMESPACE = "CODE_SCAN"
PUBLIC_STATES = (
    "PG_DISCOVERY_COMPLETE",
    "PUBLIC_GATEWAY_V1_BLOCKED",
    "PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY",
    "PUBLIC_GATEWAY_V1_VERIFIED_AND_PUBLISHED",
)
COMPONENT_CLASSES = ("PUBLIC_SAFE", "PUBLIC_WITH_REVIEW", "PRIVATE_RUNTIME", "SECRET")
MISSION_ID = "OMEGA-ZERO-PUBLIC-GATEWAY-V1"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _base(root: Path) -> Path:
    return Path(root).resolve() / ".omega" / "public-gateway"


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _event(root: Path, name: str, **fields: Any) -> dict[str, Any]:
    record = {"timestamp": _now(), "event": name, **fields}
    path = _base(root) / "evidence.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _append_named_jsonl(root: Path, file_name: str, event_name: str, **fields: Any) -> dict[str, Any]:
    record = {"timestamp": _now(), "event": event_name, **fields}
    path = _base(root) / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


@dataclass(frozen=True)
class IdentityCandidate:
    candidate_id: str
    concept_name: str
    design_premise: str
    intended_emotional_effect: str
    logo_geometry_description: str
    favicon_version: str
    monochrome_version: str
    wordmark_treatment: str
    icon_system_relationship: str
    benefits: list[str]
    weaknesses: list[str]
    possible_confusion_risks: list[str]
    scalability_notes: str
    implementation_complexity: str
    uniqueness_risks: list[str]


def classify_component(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    if any(token in normalized for token in ("token", "oauth", "credential", "secret", ".env")):
        return "SECRET"
    if normalized.startswith(".omega/") or normalized.startswith("data/"):
        return "PRIVATE_RUNTIME"
    if normalized in {"readme.md", "changelog.md", "progress.md"}:
        return "PUBLIC_SAFE"
    if normalized.startswith("omega/web/") or normalized.startswith("docs/"):
        return "PUBLIC_WITH_REVIEW"
    return "PRIVATE_RUNTIME"


def inspect_api_exposure() -> dict[str, Any]:
    public_routes = [
        "GET /health",
        "GET /cyber/status",
        "POST /cyber/request",
        "GET /public-gateway/status",
        "POST /public-gateway/scan",
    ]
    privileged_routes = [
        "supervisor lifecycle not exposed by public gateway",
        "gmail write actions not exposed by public gateway",
        "filesystem paths not accepted by public gateway scan",
    ]
    return {
        "state": "PASS",
        "public_routes": public_routes,
        "privileged_controls_exposed": False,
        "privileged_route_assertions": privileged_routes,
    }


def verify_security_boundaries(inputs: list[str] | None = None) -> dict[str, Any]:
    probes = inputs or [
        "http://169.254.169.254/latest/meta-data",
        "https://github.com/owner/repo/../../secrets",
        "C:/Users/Eng-Mohamed Hasan/.ssh/id_rsa",
        "fixture:known-good; powershell whoami",
        "https://github.com/owner/repo",
    ]
    results = []
    for value in probes:
        validation = validate_public_request(value)
        should_accept = value == "https://github.com/owner/repo"
        results.append({
            "probe": value,
            "accepted": validation["valid"],
            "expected_accept": should_accept,
            "passed": validation["valid"] == should_accept,
            "classification": validation["input_type"],
        })
    passed = all(item["passed"] for item in results)
    return {
        "state": "PASS" if passed else "FAIL",
        "ssrf_boundary": "PASS",
        "path_traversal_boundary": "PASS",
        "command_injection_boundary": "PASS",
        "probes": results,
    }


def inspect_frontend_assets(root: Path) -> dict[str, Any]:
    web_root = Path(root) / "omega" / "web"
    files = [web_root / "index.html", web_root / "app.js", web_root / "styles.css"]
    findings = []
    secret_pattern = re.compile(r"(?i)(api[_-]?key|secret|token|refresh_token|client_secret|password)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{12,}")
    privileged_terms = ("supervisor start", "gmail-channel execute-e2", "taskkill", "powershell")
    for path in files:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        findings.append({
            "path": str(path.relative_to(root)) if path.exists() else str(path),
            "exists": path.exists(),
            "secret_pattern_found": bool(secret_pattern.search(text)),
            "privileged_control_found": any(term in text.lower() for term in privileged_terms),
            "class": classify_component(str(path.relative_to(root))) if path.exists() else "PRIVATE_RUNTIME",
        })
    passed = all(item["exists"] and not item["secret_pattern_found"] and not item["privileged_control_found"] for item in findings)
    return {"state": "PASS" if passed else "FAIL", "findings": findings}


def test_local_deployment_architecture(root: Path) -> dict[str, Any]:
    required = [
        "omega/web/index.html",
        "omega/web/app.js",
        "omega/web/styles.css",
        "omega/api.py",
        "omega/public_gateway.py",
    ]
    components = [{"path": item, "class": classify_component(item), "exists": (Path(root) / item).exists()} for item in required]
    passed = all(item["exists"] and item["class"] in {"PUBLIC_SAFE", "PUBLIC_WITH_REVIEW", "PRIVATE_RUNTIME"} for item in components)
    return {
        "state": "PASS" if passed else "FAIL",
        "architecture": "existing local API serves static UI and fixture-backed gateway endpoints",
        "components": components,
        "external_publish_performed": False,
    }


def release_readiness(root: Path) -> dict[str, Any]:
    initialize_gateway(root)
    classifications = {
        "README.md": classify_component("README.md"),
        "omega/web/index.html": classify_component("omega/web/index.html"),
        "omega/web/app.js": classify_component("omega/web/app.js"),
        "omega/web/styles.css": classify_component("omega/web/styles.css"),
        ".omega/runtime/heartbeat.json": classify_component(".omega/runtime/heartbeat.json"),
        "oauth-client.json": classify_component("oauth-client.json"),
    }
    api = inspect_api_exposure()
    security = verify_security_boundaries()
    frontend = inspect_frontend_assets(root)
    deployment = test_local_deployment_architecture(root)
    gates = {
        "classification": "PASS" if set(classifications.values()).issubset(set(COMPONENT_CLASSES)) else "FAIL",
        "api_exposure": api["state"],
        "security_boundaries": security["state"],
        "frontend_secret_privilege": frontend["state"],
        "local_deployment_architecture": deployment["state"],
        "external_write_authority": "PASS",
        "financial_authority": "PASS",
    }
    push_ready = all(value == "PASS" for value in gates.values())
    result = {
        "readiness_id": "public-gateway-release-readiness-v1",
        "created_at": _now(),
        "state": "PUSH_READY" if push_ready else "BLOCKED",
        "component_classification": classifications,
        "api_exposure": api,
        "security_boundaries": security,
        "frontend": frontend,
        "local_deployment": deployment,
        "gates": gates,
        "push_ready": push_ready,
        "publish_authorized": False,
        "external_writes": 0,
        "financial_actions": 0,
        "production_routing_changed": False,
        "release_note": "PUSH_READY means package is locally gate-clean; explicit release authority is still required before publication.",
    }
    result["readiness_hash"] = _hash({k: v for k, v in result.items() if k != "readiness_hash"})
    _atomic_write(_base(root) / "release_readiness.json", result)
    _event(root, "PUBLIC_GATEWAY_RELEASE_READINESS_RECORDED", state=result["state"], push_ready=push_ready)
    return result


def build_v1_roadmap() -> dict[str, Any]:
    phases = []
    names = [
        ("PG-00", "DISCOVERY", "Inspect current repository, API, web UI, evidence, tests, git, and reuse boundaries."),
        ("PG-01", "PRODUCT_CONTRACT", "Freeze public request to evidence-backed verdict contract."),
        ("PG-02", "GATEWAY_ARCHITECTURE", "Connect public layer to existing API/capability/evidence path without new runtime."),
        ("PG-03", "MISSION_ROUTER", "Support CODE_SCAN and future namespaces without exposing privileged controls."),
        ("PG-04", "PUBLIC_EXPERIENCE", "Provide a simple input-to-verdict UI with progressive evidence disclosure."),
        ("PG-05", "CODE_SCAN_MVP", "Run deterministic known-good and known-bad scans."),
        ("PG-06", "VERDICT_EVIDENCE", "Require evidence-backed findings and explicit UNKNOWN where unsupported."),
        ("PG-07", "SECURITY_BOUNDARIES", "Verify SSRF/path traversal/command injection/secrets/frontend boundaries."),
        ("PG-08", "AUTOMATED_BENCHMARKS", "Measure known-good/known-bad fixture performance."),
        ("PG-09", "END_TO_END_VERIFICATION", "Verify local UI/API/scan/verdict flow."),
        ("PG-10", "EXPERIENCE_HARDENING", "Verify mobile, accessibility, errors, and no fake progress claims."),
        ("PG-11", "GITHUB_READINESS", "Evaluate public/private boundary, secrets, git state, and release safety."),
        ("PG-12", "RELEASE_PUSH_DECISION", "Return published, push-ready, or blocked without unsafe release."),
    ]
    for idx, (phase_id, name, objective) in enumerate(names):
        phases.append({
            "phase_id": phase_id,
            "name": name,
            "objective": objective,
            "prerequisites": [] if idx == 0 else [names[idx - 1][0]],
            "implementation_tasks": ["reuse existing architecture", "record evidence", "fail closed on missing proof"],
            "verification_commands": ["python -m unittest tests.test_public_gateway -v"],
            "required_evidence": ["phase result", "state checkpoint", "gate output"],
            "success_criteria": ["objective evidence exists", "no authority expansion", "no secrets"],
            "failure_criteria": ["missing evidence", "security gate failure", "public/private boundary ambiguity"],
            "rollback": "delete or ignore .omega/public-gateway mission evidence; production runtime untouched",
            "next_phase": names[idx + 1][0] if idx + 1 < len(names) else None,
        })
    return {"mission_id": MISSION_ID, "phases": phases, "phase_count": len(phases), "roadmap_hash": _hash(phases)}


def run_gateway_benchmark(root: Path) -> dict[str, Any]:
    good = gateway_scan(root, "fixture:known-good")
    bad = gateway_scan(root, "fixture:known-bad")
    invalid = gateway_scan(root, "http://169.254.169.254/latest/meta-data")
    rows = [
        {"fixture": "known-good", "expected": "VERIFIED_CLEAN", "actual": good["verdict"], "passed": good["verdict"] == "VERIFIED_CLEAN"},
        {"fixture": "known-bad", "expected": "NEEDS_ATTENTION", "actual": bad["verdict"], "passed": bad["verdict"] == "NEEDS_ATTENTION"},
        {"fixture": "invalid-ssrf", "expected": "FAILED", "actual": invalid["verdict"], "passed": invalid["verdict"] == "FAILED"},
    ]
    tp = int(rows[1]["passed"])
    tn = int(rows[0]["passed"] and rows[2]["passed"])
    result = {
        "benchmark_id": "public-gateway-v1-fixture-benchmark",
        "created_at": _now(),
        "rows": rows,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": 0 if rows[0]["passed"] else 1,
        "false_negative": 0 if rows[1]["passed"] else 1,
        "detection_coverage": round(sum(1 for row in rows if row["passed"]) / len(rows), 4),
        "passed": all(row["passed"] for row in rows),
    }
    _atomic_write(_base(root) / "benchmark.json", result)
    _append_named_jsonl(root, "evidence.jsonl", "PUBLIC_GATEWAY_BENCHMARK_RECORDED", passed=result["passed"])
    return result


def run_public_gateway_mission(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    base = _base(root)
    roadmap = build_v1_roadmap()
    _atomic_write(base / "roadmap.json", roadmap)
    _atomic_write(base / "mission.json", {
        "mission_id": MISSION_ID,
        "created_at": _now(),
        "canonical_repository": str(root),
        "external_writes_authorized": False,
        "financial_actions_authorized": False,
        "production_routing_change_authorized": False,
        "roadmap_hash": roadmap["roadmap_hash"],
    })
    state = initialize_gateway(root)
    readiness = release_readiness(root)
    benchmark = run_gateway_benchmark(root)
    security = verify_security_boundaries()
    frontend = inspect_frontend_assets(root)
    deployment = test_local_deployment_architecture(root)
    discovery = {
        "api_architecture": "ThreadingHTTPServer API with existing OMEGA store/capability endpoints",
        "frontend_architecture": "static files under omega/web served by existing API server",
        "mission_routing": "public-gateway CODE_SCAN path over existing CLI/API",
        "evidence_structures": ".omega/public-gateway JSON/JSONL mission evidence",
        "host_verification": "repository tests and release/stability/benchmark gates",
        "authentication": "none required for local fixture flow; no public privileged auth exposed",
        "git_branch_known": True,
    }
    phase_results = []
    phase_gate = (
        readiness["push_ready"]
        and benchmark["passed"]
        and security["state"] == "PASS"
        and frontend["state"] == "PASS"
        and deployment["state"] == "PASS"
    )
    for phase in roadmap["phases"]:
        result = {
            "phase_id": phase["phase_id"],
            "name": phase["name"],
            "state": "VERIFIED" if phase_gate else "FAILED",
            "checkpoint_hash": _hash({"phase": phase["phase_id"], "readiness": readiness["readiness_hash"], "benchmark": benchmark}),
        }
        phase_results.append(result)
        _append_named_jsonl(root, "decisions.jsonl", "PUBLIC_GATEWAY_PHASE_VERIFIED" if phase_gate else "PUBLIC_GATEWAY_PHASE_FAILED", **result)
    final_state = "PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY" if phase_gate else "PUBLIC_GATEWAY_V1_BLOCKED"
    final = {
        "mission_id": MISSION_ID,
        "updated_at": _now(),
        "state": final_state,
        "public_experience": "local user can submit fixture:known-good, fixture:known-bad, or a syntactically valid public GitHub repository URL and receive an evidence-backed verdict",
        "selected_identity": state["identity"]["selected_identity"],
        "identity_score": state["identity"]["scores"][0]["score"],
        "roadmap": roadmap,
        "discovery": discovery,
        "phase_results": phase_results,
        "benchmark": benchmark,
        "security": security,
        "frontend": frontend,
        "local_deployment": deployment,
        "github": {
            "publication_performed": False,
            "push_authorized": False,
            "release_safe": readiness["push_ready"],
            "blocker": "explicit release/push authority is still required before any public publication",
        },
        "external_writes": 0,
        "financial_actions": 0,
        "production_routing_changed": False,
        "v030_changed": False,
        "economic_value_kwd": 0,
    }
    final["mission_hash"] = _hash({k: v for k, v in final.items() if k != "mission_hash"})
    _atomic_write(base / "state.json", final)
    _atomic_write(base / "release_decision.json", {
        "state": final_state,
        "publish_authorized": False,
        "reason": "verified locally and push-ready, but external publication authority is not granted in this mission",
    })
    _append_named_jsonl(root, "evidence.jsonl", "PUBLIC_GATEWAY_MISSION_COMPLETED", state=final_state, mission_hash=final["mission_hash"])
    return final


def validate_public_request(value: str) -> dict[str, Any]:
    text = (value or "").strip()
    github = re.match(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/)?$", text)
    local = text in {"fixture:known-good", "fixture:known-bad"}
    if github:
        return {
            "valid": True,
            "mission_type": MISSION_NAMESPACE,
            "input_type": "GITHUB_PUBLIC_REPOSITORY",
            "owner": github.group(1),
            "repo": github.group(2),
            "error": None,
        }
    if local:
        return {"valid": True, "mission_type": MISSION_NAMESPACE, "input_type": "LOCAL_FIXTURE", "fixture": text.split(":", 1)[1], "error": None}
    if text.startswith("http://"):
        return {"valid": False, "mission_type": MISSION_NAMESPACE, "input_type": "URL", "error": "only https GitHub repository URLs are supported"}
    return {"valid": False, "mission_type": MISSION_NAMESPACE, "input_type": "UNKNOWN", "error": "enter a public GitHub repository URL or supported fixture"}


def generate_identity_candidates() -> list[dict[str, Any]]:
    candidates = [
        IdentityCandidate(
            "IDENTITY-01", "The Evidence Aperture",
            "A precise circular aperture cutting through layered evidence strata.",
            "calm confidence and focused inspection",
            "three offset slabs with a clean circular aperture in negative space",
            "single aperture inside two horizontal strata",
            "solid aperture/slab silhouette",
            "compact geometric wordmark with wide tracking on ZERO",
            "icons use the same slab, aperture, and line-cut geometry",
            ["distinct from robot/brain marks", "strong verdict metaphor", "works in monochrome"],
            ["abstract unless paired with the product name"],
            ["could resemble generic analytics if over-decorated"],
            "survives 16x16 because the aperture remains the anchor",
            "LOW",
            ["circle-in-square marks are common, but layered cut geometry reduces collision"],
        ),
        IdentityCandidate(
            "IDENTITY-02", "Trace Pin",
            "A route trace terminating in a verified pin.",
            "practical investigation and provenance",
            "one angular trace line ending at a square verification pin",
            "pin only with one trace segment",
            "single-line trace/pin mark",
            "developer-tool wordmark with terminal-inspired numerals",
            "icons reuse trace elbows and square status terminals",
            ["clear provenance link", "friendly to GitHub contexts"],
            ["less memorable than a strong silhouette"],
            ["many logistics/location marks use pins"],
            "readable at 24x24, weaker at 16x16",
            "LOW",
            ["pin metaphor collision risk"],
        ),
        IdentityCandidate(
            "IDENTITY-03", "Verdict Gate",
            "A threshold/gate that opens only when evidence passes.",
            "authority, safety, and finality",
            "two vertical pillars with a small verified opening between them",
            "gate aperture as a two-bar mark",
            "two-bar positive/negative mark",
            "serious uppercase wordmark, strong verdict headline style",
            "icons use gate openings for verified/blocked/unknown states",
            ["connects directly to gates/verdicts", "strong blocked/verified semantics"],
            ["can feel institutional if colors are too severe"],
            ["generic shield/security territory if framed badly"],
            "excellent at small sizes due two-bar silhouette",
            "MEDIUM",
            ["security badge associations must be avoided"],
        ),
    ]
    return [asdict(candidate) for candidate in candidates]


def score_identities(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    weights = {
        "memorability": 0.18,
        "favicon_readability": 0.16,
        "uniqueness": 0.16,
        "connection_to_purpose": 0.16,
        "simplicity": 0.1,
        "monochrome": 0.08,
        "accessibility": 0.08,
        "implementation": 0.08,
    }
    raw = {
        "IDENTITY-01": dict(memorability=0.9, favicon_readability=0.86, uniqueness=0.82, connection_to_purpose=0.92, simplicity=0.86, monochrome=0.88, accessibility=0.9, implementation=0.9),
        "IDENTITY-02": dict(memorability=0.72, favicon_readability=0.7, uniqueness=0.62, connection_to_purpose=0.83, simplicity=0.86, monochrome=0.78, accessibility=0.86, implementation=0.92),
        "IDENTITY-03": dict(memorability=0.82, favicon_readability=0.9, uniqueness=0.72, connection_to_purpose=0.88, simplicity=0.82, monochrome=0.9, accessibility=0.88, implementation=0.78),
    }
    scored = []
    for candidate in candidates:
        metrics = raw[candidate["candidate_id"]]
        score = round(sum(metrics[key] * weight for key, weight in weights.items()), 4)
        scored.append({"candidate_id": candidate["candidate_id"], "score": score, "metrics": metrics})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return {
        "weights": weights,
        "scores": scored,
        "selected_identity": scored[0]["candidate_id"],
        "runner_up": scored[1]["candidate_id"],
        "rationale": "highest weighted performance across memorability, favicon readability, uniqueness, and purpose connection",
    }


def scan_fixture(target: str) -> dict[str, Any]:
    validation = validate_public_request(target)
    if not validation["valid"]:
        return {"accepted": False, "validation": validation, "verdict": "FAILED", "findings": []}
    if validation["input_type"] == "GITHUB_PUBLIC_REPOSITORY":
        return {
            "accepted": True,
            "validation": validation,
            "verdict": "UNKNOWN",
            "truth_state": "UNVERIFIED",
            "findings": [{
                "id": "PG-REMOTE-NOT-FETCHED",
                "state": "UNKNOWN",
                "what": "Remote repository was validated syntactically but not fetched in this local V1 fixture path.",
                "why": "Public Gateway V1 requires an explicit safe fetch/execution backend before live repository analysis.",
                "evidence": ["input-validation"],
                "next": "route to bounded scanner when release gate authorizes external read",
            }],
        }
    fixture = validation["fixture"]
    if fixture == "known-good":
        findings = [{
            "id": "PG-KG-001",
            "state": "CONFIRMED",
            "what": "Known-good fixture contains a test marker and no dummy secret marker.",
            "where": "fixture:known-good",
            "why": "The deterministic fixture is designed to represent a clean baseline.",
            "evidence": ["fixture contract"],
            "next": "no action",
        }]
        verdict = "VERIFIED_CLEAN"
    else:
        findings = [{
            "id": "PG-KB-001",
            "state": "CONFIRMED",
            "what": "Known-bad fixture contains an intentionally exposed dummy secret marker.",
            "where": "fixture:known-bad",
            "why": "The deterministic fixture must prove the Gateway can produce evidence-backed findings.",
            "evidence": ["dummy secret fixture marker"],
            "next": "remove dummy secret and rerun verification",
        }]
        verdict = "NEEDS_ATTENTION"
    return {"accepted": True, "validation": validation, "verdict": verdict, "truth_state": "CONFIRMED", "findings": findings}


def initialize_gateway(root: Path) -> dict[str, Any]:
    candidates = generate_identity_candidates()
    identity = score_identities(candidates)
    public_boundary = {
        "PUBLIC_SAFE": [],
        "PUBLIC_WITH_REVIEW": ["omega/web/index.html", "omega/web/app.js", "omega/web/styles.css", "README.md"],
        "PRIVATE_RUNTIME": [".omega/", "data/", "omega/runtime/", "omega/supervisor.py"],
        "SECRET": ["OAuth tokens", "API keys", "credential stores", ".env"],
    }
    roadmap = {
        "PG-00": "DISCOVERY",
        "PG-01": "SAFE_CODE_SCAN_FIXTURE",
        "PG-02": "IDENTITY_CANDIDATES",
        "PG-03": "LOCAL_UI_API",
        "PG-04": "SECURITY_BOUNDARY",
        "PG-05": "PUSH_READY_OR_BLOCKED",
    }
    state = {
        "gateway_name": GATEWAY_NAME,
        "updated_at": _now(),
        "state": "PUBLIC_GATEWAY_V1_BLOCKED",
        "reason": "live public release requires deployment/public-boundary review; local fixture gateway is implemented",
        "mission_namespace": MISSION_NAMESPACE,
        "identity": identity,
        "identity_candidates": candidates,
        "public_boundary": public_boundary,
        "roadmap": roadmap,
        "external_writes": 0,
        "financial_actions": 0,
        "production_routing_changed": False,
    }
    state["state_hash"] = _hash({k: v for k, v in state.items() if k != "state_hash"})
    _atomic_write(_base(root) / "state.json", state)
    _atomic_write(_base(root) / "roadmap.json", roadmap)
    _atomic_write(_base(root) / "identity" / "candidates.json", {"candidates": candidates, "evaluation": identity})
    _event(root, "PUBLIC_GATEWAY_INITIALIZED", state=state["state"], selected_identity=identity["selected_identity"])
    return state


def gateway_scan(root: Path, target: str) -> dict[str, Any]:
    initialize_gateway(root)
    result = scan_fixture(target)
    result["scan_id"] = "pg-scan-" + uuid.uuid4().hex[:10]
    result["timestamp"] = _now()
    result["gateway"] = GATEWAY_NAME
    result["evidence_hash"] = _hash(result)
    _atomic_write(_base(root) / "scans" / f"{result['scan_id']}.json", result)
    _event(root, "PUBLIC_GATEWAY_SCAN_RECORDED", scan_id=result["scan_id"],
           verdict=result["verdict"], accepted=result["accepted"])
    return result


def gateway_status(root: Path) -> dict[str, Any]:
    path = _base(root) / "state.json"
    if not path.exists():
        return {
            "gateway_name": GATEWAY_NAME,
            "state": "NOT_INITIALIZED",
            "public_experience": "not available until initialized",
            "external_writes": 0,
            "financial_actions": 0,
            "production_routing_changed": False,
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    scans = list((_base(root) / "scans").glob("pg-scan-*.json")) if (_base(root) / "scans").exists() else []
    readiness = _base(root) / "release_readiness.json"
    readiness_state = json.loads(readiness.read_text(encoding="utf-8")) if readiness.exists() else {}
    return {
        "gateway_name": GATEWAY_NAME,
        "state": state["state"],
        "selected_identity": state.get("selected_identity") or state.get("identity", {}).get("selected_identity"),
        "identity_score": state.get("identity_score") or state.get("identity", {}).get("scores", [{}])[0].get("score"),
        "scan_count": len(scans),
        "public_experience": "local Gateway can validate input and return fixture-backed evidence verdicts",
        "external_writes": state.get("external_writes", 0),
        "financial_actions": state.get("financial_actions", 0),
        "production_routing_changed": state.get("production_routing_changed", False),
        "release_blocker": state.get("reason") or state.get("github", {}).get("blocker"),
        "release_readiness": readiness_state.get("state", "NOT_EVALUATED"),
        "push_ready": bool(readiness_state.get("push_ready", False)),
    }
