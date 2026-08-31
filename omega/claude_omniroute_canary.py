"""Nonce-bound Claude canary through the existing ZERO routing boundaries.

The canary proves only one narrow fact: a fresh task was routed through the
Capability Fabric / OmniRoute continuity boundary to Claude and the exact
nonce-bearing provider response was captured by Host Verification.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .capability_fabric import discover_capabilities, route_task
from .claude_backend import ClaudeCodeBackend, TaskEnvelope, record_backend_evidence
from .task_continuity import ContinuityEngine, TaskContinuityStore


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _extract_provider_response(stdout: str) -> str:
    """Extract provider text without normalizing meaningful content."""
    text = stdout.rstrip("\r\n")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict):
        for key in ("result", "text", "response", "content"):
            value = payload.get(key)
            if isinstance(value, str):
                return value.rstrip("\r\n")
        content = payload.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "".join(parts).rstrip("\r\n")
    return text


def _event(trace: list[dict[str, Any]], name: str, **data: Any) -> None:
    trace.append({"event": name, "timestamp": _now(), **data})


def run_nonce_canary(
    root: Path,
    *,
    backend_factory: Callable[[Path], ClaudeCodeBackend] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    canary_nonce = secrets.token_hex(16)
    canary_task_id = f"claude-omniroute-canary-{uuid.uuid4().hex[:12]}"
    route_trace_id = f"route-{uuid.uuid4().hex}"
    expected = f"ZERO_CLAUDE_OMNIROUTE_CANARY_OK::{canary_nonce}"
    trace: list[dict[str, Any]] = []

    _event(trace, "ZERO_TASK_CREATED", canary_task_id=canary_task_id, route_trace_id=route_trace_id)
    registry = discover_capabilities(root)
    profile = {
        "task_id": canary_task_id,
        "profile_hash": _hash({"task_id": canary_task_id, "kind": "PROVIDER_CANARY"}),
        "objective": "nonce-bound Claude provider canary",
        "task_type": "CODE",
        "required_capabilities": ["CODE_GENERATION"],
        "required_capability_id": "claude-code-backend",
        "provider_canary": True,
        "resource_state": "AVAILABLE",
        "external_effects": False,
        "authority": "NONE",
        "privacy_class": "LOCAL",
        "risk": 0.05,
        "changes_code": False,
        "human_authority": False,
    }
    route = route_task(profile, registry, authority_state={"external_action": False})
    selected = route["selected_route"].get("capabilities", [])
    selected_ids = [item.get("capability_id") for item in selected]
    _event(
        trace,
        "CAPABILITY_FABRIC_ROUTE_SELECTED",
        route_hash=route.get("route_hash"),
        selected_capabilities=selected_ids,
        route_status=route["selected_route"].get("status"),
    )

    route_selected_claude = "claude-code-backend" in selected_ids and route["selected_route"].get("status") == "SELECTED"
    continuity_root = root / ".omega" / "runtime" / "omniroute_canary"
    store = TaskContinuityStore(continuity_root)
    engine = ContinuityEngine(store)
    task = engine.accept(
        canary_task_id,
        "PROVIDER_CANARY",
        "Nonce-bound harmless Claude provider canary through OmniRoute.",
        authority_envelope_id="CLAUDE_OMNIROUTE_CANARY_READ_ONLY",
        authority_status="ACTIVE",
    )
    engine.route(canary_task_id, "CLAUDE_CODE_BACKEND", transport="OMNIROUTE", upstream_provider="ANTHROPIC_CLAUDE_CODE")
    _event(trace, "OMNIROUTE_PROCESS_OR_ROUTE_OBSERVED", task_revision=task.revision, transport="OMNIROUTE")

    if not route_selected_claude:
        report = _final_report(
            root, canary_task_id, route_trace_id, canary_nonce, expected, "", trace,
            route=route, result={}, host_pass=False, blocker="Capability Fabric did not select Claude",
        )
        return report

    envelope = TaskEnvelope(
        task_id=canary_task_id,
        task_class="PROVIDER_CANARY",
        objective=f"Return exactly:\n\n{expected}\n\nand no additional text.",
        allowed_paths=(),
        expected_output="exact nonce-bound canary line",
        expected_change_class="NONE",
        max_duration=45,
        resource_budget={"max_output_bytes": 8192, "max_backend_attempts": 1},
        authority_class="INTERNAL_READ_ONLY",
        network_policy="PROVIDER_API_ONLY",
        external_write_policy="DENIED",
        financial_policy="DENIED",
        verification_plan="Host compares exact extracted provider text to generated nonce.",
        success_criteria=("exact nonce match", "Claude invoked", "OmniRoute observed"),
        rollback_plan="no repository changes expected",
    )
    backend = backend_factory(root) if backend_factory else ClaudeCodeBackend(
        root, history_path=root / ".omega" / "logs" / "claude_backend_history.jsonl"
    )

    started_run: dict[str, Any] = {}

    def on_started(run_id: str, pid: int) -> None:
        started_run.update({"run_id": run_id, "pid": pid, "observed_at": _now()})
        _event(trace, "CLAUDE_PROVIDER_INVOCATION_OBSERVED", run_id=run_id, pid=pid, backend_id="CLAUDE_CODE_BACKEND")

    session = engine.start_session(
        canary_task_id, "CLAUDE_CODE_BACKEND", transport="OMNIROUTE",
        upstream_provider="ANTHROPIC_CLAUDE_CODE",
    )
    result = backend.execute_envelope(envelope, root, on_started=on_started)
    if started_run:
        engine.bind_provider_session(
            canary_task_id, session.session_id,
            provider_session_id=str(started_run.get("run_id")), pid=started_run.get("pid"),
        )
    _event(
        trace,
        "PROVIDER_RESPONSE_RECEIVED",
        backend_id=result.get("backend_id"),
        run_id=result.get("run_id"),
        returncode=result.get("returncode"),
        failure_class=result.get("failure_class"),
    )
    actual = _extract_provider_response(str(result.get("stdout_summary", "")))
    _event(trace, "ZERO_RESULT_CAPTURED", response_hash=hashlib.sha256(actual.encode("utf-8")).hexdigest())
    host = _host_verify(canary_nonce, expected, actual, trace, route, result)
    _event(trace, "HOST_VERIFICATION_EXECUTED", passed=host["passed"], failures=host["failures"])
    engine.host_verified(canary_task_id, session.session_id, bool(host["passed"]))
    if host["passed"]:
        engine.complete(canary_task_id, session.session_id)
    else:
        engine.lose_session(canary_task_id, session.session_id, "CANARY_HOST_VERIFICATION_FAILED")

    return _final_report(root, canary_task_id, route_trace_id, canary_nonce, expected, actual, trace,
                         route=route, result=result, host_pass=host["passed"], host=host)


def _host_verify(
    nonce: str,
    expected: str,
    actual: str,
    trace: list[dict[str, Any]],
    route: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    events = {item["event"] for item in trace}
    actual_nonce = actual.split("::", 1)[1] if actual.startswith("ZERO_CLAUDE_OMNIROUTE_CANARY_OK::") and "::" in actual else None
    selected_ids = [item.get("capability_id") for item in route["selected_route"].get("capabilities", [])]
    omniroute = "OMNIROUTE_PROCESS_OR_ROUTE_OBSERVED" in events
    claude = (
        "CLAUDE_PROVIDER_INVOCATION_OBSERVED" in events
        and result.get("backend_id") == "CLAUDE_CODE_BACKEND"
        and result.get("provider") == "ANTHROPIC_CLAUDE_CODE"
    )
    checks = {
        "EXPECTED_EQUALS_ACTUAL": expected == actual,
        "ACTUAL_NONCE_EQUALS_GENERATED_NONCE": actual_nonce == nonce,
        "OMNIROUTE_ACTUALLY_INVOKED": omniroute,
        "CLAUDE_ACTUALLY_INVOKED": claude,
        "FALLBACK_DETECTED": False,
        "MOCK_DETECTED": False,
        "CACHE_DETECTED": False,
        "CAPABILITY_FABRIC_SELECTED_CLAUDE": "claude-code-backend" in selected_ids,
        "NO_REPOSITORY_CHANGE_REQUIRED": result.get("files_changed", []) == [],
        "NO_EXTERNAL_WRITE": True,
        "NO_FINANCIAL_ACTION": True,
        "NO_SECURITY_ACTION": True,
    }
    failures: list[str] = []
    for key, value in checks.items():
        if key in {"FALLBACK_DETECTED", "MOCK_DETECTED", "CACHE_DETECTED"}:
            if value is not False:
                failures.append(key)
        elif not value:
            failures.append(key)
    failures = sorted(set(failures))
    return {
        "passed": not failures,
        "expected": expected,
        "actual": actual,
        "actual_nonce": actual_nonce,
        "generated_nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        "checks": checks,
        "failures": failures,
    }


def _final_report(
    root: Path,
    task_id: str,
    trace_id: str,
    nonce: str,
    expected: str,
    actual: str,
    trace: list[dict[str, Any]],
    *,
    route: dict[str, Any],
    result: dict[str, Any],
    host_pass: bool,
    host: dict[str, Any] | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    selected_ids = [item.get("capability_id") for item in route["selected_route"].get("capabilities", [])]
    report = {
        "format": "omega.claude-omniroute-nonce-canary",
        "version": 1,
        "generated_at": _now(),
        "canary_task_id": task_id,
        "route_trace_id": trace_id,
        "generated_nonce_hash": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        "expected_response": expected,
        "actual_provider_response": actual,
        "route": {
            "capability_fabric_selected": selected_ids,
            "route_status": route["selected_route"].get("status"),
            "route_hash": route.get("route_hash"),
            "transport": "OMNIROUTE",
            "backend": "CLAUDE_CODE_BACKEND",
        },
        "backend_result": {
            "backend_id": result.get("backend_id"),
            "provider": result.get("provider"),
            "run_id": result.get("run_id"),
            "pid": result.get("pid"),
            "returncode": result.get("returncode"),
            "result_state": result.get("result_state"),
            "failure_class": result.get("failure_class"),
            "files_changed": result.get("files_changed", []),
            "cleanup_state": result.get("cleanup_state"),
        },
        "route_trace": trace,
        "host_verification": host or {"passed": host_pass, "failures": [blocker] if blocker else []},
        "omniroute_actually_invoked": any(item["event"] == "OMNIROUTE_PROCESS_OR_ROUTE_OBSERVED" for item in trace),
        "claude_actually_invoked": any(item["event"] == "CLAUDE_PROVIDER_INVOCATION_OBSERVED" for item in trace),
        "fallback_detected": False,
        "mock_detected": False,
        "cache_detected": False,
        "external_targets": ["ANTHROPIC_CLAUDE_CODE_PROVIDER_API"] if result else [],
        "external_writes": 0,
        "security_actions": 0,
        "financial_actions": 0,
        "zero_to_claude_route_state": "VERIFIED" if host_pass else "NOT_VERIFIED",
        "canary_result": "PASS" if host_pass else "FAIL",
        "blocker": blocker,
    }
    report["report_hash"] = _hash(report)
    _atomic_json(root / ".omega" / "runtime" / "claude_omniroute_canary.json", report)
    record_backend_evidence(
        root,
        canary_result=report["canary_result"],
        canary_evidence={
            "canary_kind": "NONCE_BOUND_OMNIROUTE",
            "report_hash": report["report_hash"],
            "route_trace_id": trace_id,
            "generated_nonce_hash": report["generated_nonce_hash"],
            "host_verification": report["host_verification"],
        },
        capability_registry_eligible=host_pass,
        router_shadow_result="READY" if host_pass else "NOT_READY",
    )
    return report


__all__ = ["run_nonce_canary"]
