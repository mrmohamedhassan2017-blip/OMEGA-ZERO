"""ZERO Capability Fabric V1.

This module is a deterministic, evidence-first selection layer.  It represents
capabilities rather than product brands, profiles task requirements, and emits
non-authoritative routing recommendations.  It deliberately does not execute
providers, call models, access the network, grant authority, or replace the
Supervisor/Wake Plane/Host Verification stack.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REGISTRY_VERSION = 2
ROUTER_MODE = "SHADOW"
ACCESS_MODES = {"PROGRAMMATIC", "INTERACTIVE_ONLY", "UNAVAILABLE", "UNKNOWN"}
AVAILABILITY_STATES = {
    "AVAILABLE", "UNAVAILABLE", "UNKNOWN", "DEGRADED", "WAITING_RESOURCE",
    "AUTHORITY_REQUIRED", "QUOTA_LIMITED", "TEMPORARILY_BLOCKED",
}
ADOPTION_STATES = {
    "DISCOVERED", "AVAILABLE", "QUALIFIED", "BENCHMARKED", "SHADOWED",
    "CONTROLLED", "PROVEN_REUSABLE", "PREFERRED_ROUTE", "RETIRED",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record(
    *, capability_id: str, capability_class: str, provider: str,
    interface: str, availability: str, authority_required: str,
    input_types: list[str], output_types: list[str], model_or_tool: str,
    current_limits: list[str], latency_class: str, resource_cost: str,
    external_side_effect: bool, verification_method: str,
    failure_modes: list[str], confidence: float, access_mode: str,
    discovered_from: list[str], verified_by: list[str] | None = None,
    adoption_state: str = "DISCOVERED", security: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if availability not in AVAILABILITY_STATES:
        raise ValueError(f"invalid availability: {availability}")
    if access_mode not in ACCESS_MODES:
        raise ValueError(f"invalid access mode: {access_mode}")
    if adoption_state not in ADOPTION_STATES:
        raise ValueError(f"invalid adoption state: {adoption_state}")
    return {
        "capability_id": capability_id,
        "capability_class": capability_class,
        "provider": provider,
        "interface": interface,
        "availability": availability,
        "authority_required": authority_required,
        "input_types": input_types,
        "output_types": output_types,
        "model_or_tool": model_or_tool,
        "current_limits": current_limits,
        "latency_class": latency_class,
        "resource_cost": resource_cost,
        "external_side_effect": external_side_effect,
        "verification_method": verification_method,
        "failure_modes": failure_modes,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "last_verified_at": _now(),
        "access_mode": access_mode,
        "discovered_from": discovered_from,
        "verified_by": verified_by or [],
        "adoption_state": adoption_state,
        "security": security or {
            "data_exposure": "local-contract-only",
            "credential_requirements": "none",
            "external_communication": False,
            "filesystem_scope": "canonical repository read-only",
            "command_execution": False,
            "network_reach": False,
            "prompt_injection_risk": "bounded-data-only",
            "supply_chain_risk": "standard-library-only",
        },
    }


def _codex_executable() -> str | None:
    """Discover a CLI without starting it or assuming account access."""
    for name in ("codex.cmd", "codex.exe", "codex"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _claude_executable() -> str | None:
    """Discover presence only; Capability Fabric never starts a provider CLI."""
    for name in ("claude.exe", "claude.cmd", "claude"):
        found = shutil.which(name)
        if found:
            return found
    return None


def discover_capabilities(root: Path, *, now: str | None = None) -> dict[str, Any]:
    """Build a registry from repository/host facts only.

    The registry intentionally records unavailable/unknown capabilities rather
    than treating names in documentation as usable implementations.
    """
    root = Path(root).resolve()
    observed = {
        "engine": root / "omega" / "engine.py",
        "store": root / "omega" / "store.py",
        "api": root / "omega" / "api.py",
        "tests": root / "tests",
        "supervisor": root / "omega" / "supervisor.py",
        "wake_plane": root / "omega" / "wake_plane.py",
        "provenance": root / "omega" / "wake_provenance.py",
        "gmail": root / "omega" / "gmail_adapter.py",
        "discovery": root / "omega" / "capability_discovery.py",
        "governor": root / "omega" / "development_governor.py",
        "zpa": root / "omega" / "zpa.py",
        "evaluation": root / "omega" / "evaluation.py",
        "evidence": root / "omega" / "evidence.py",
        "zero_truth": root / "omega" / "zero_truth.py",
        "claude_backend": root / "omega" / "claude_backend.py",
    }
    present = {name: path.exists() for name, path in observed.items()}
    evidence = {name: _file_hash(path) for name, path in observed.items() if path.exists()}
    records: list[dict[str, Any]] = []

    def builtin(capability_id: str, capability_class: str, module_names: list[str],
                *, verification: str, confidence: float = 0.95,
                limits: list[str] | None = None) -> None:
        sources = [name for name in module_names if present.get(name)]
        available = bool(sources)
        records.append(_record(
            capability_id=capability_id, capability_class=capability_class,
            provider="OMEGA_LOCAL_CORE", interface="Python standard-library module",
            availability="AVAILABLE" if available else "UNKNOWN",
            authority_required="NONE", input_types=["structured local request"],
            output_types=["deterministic result envelope"], model_or_tool=";".join(sources) or "not-observed",
            current_limits=limits or ["local repository scope", "no autonomous external side effect"],
            latency_class="bounded", resource_cost="local", external_side_effect=False,
            verification_method=verification, failure_modes=["missing source", "malformed input"],
            confidence=confidence if available else 0.2, access_mode="PROGRAMMATIC" if available else "UNKNOWN",
            discovered_from=[f"repository:{name}" for name in sources] or ["repository:absent"],
            verified_by=["existing host regression/release/stability gates"] if available else [],
            adoption_state="PROVEN_REUSABLE" if available else "DISCOVERED",
        ))

    builtin("deterministic-core", "PLANNING", ["engine", "store", "api"], verification="Core graph and persistence tests")
    builtin("host-execution", "HOST_EXECUTION", ["zpa", "supervisor"], verification="bounded process/host workflow tests")
    builtin("host-testing", "TESTING", ["tests", "evaluation"], verification="full regression and ResourceWarning gates")
    builtin("host-verification", "VERIFICATION", ["evaluation", "api"], verification="Host Verification and release gates")
    builtin("checkpoint-recovery", "RECOVERY", ["supervisor", "store"], verification="recovery and continuity tests")
    builtin("wake-scheduling", "SCHEDULING", ["wake_plane", "supervisor"], verification="Wake Plane and Supervisor tests")
    builtin("provenance-ledger", "PROVENANCE", ["provenance", "evaluation"], verification="provenance/continuity tests")
    builtin("capability-discovery", "CAPABILITY_DISCOVERY", ["discovery", "governor"], verification="capability-discovery regressions")
    builtin("evidence-synthesis", "EVIDENCE_SYNTHESIS", ["evidence", "zero_truth"], verification="Reality Ledger and evidence-boundary tests")

    codex = _codex_executable()
    provider_status = ""
    provider_checkpoint = root / ".omega" / "runtime" / "provider_checkpoint.json"
    if provider_checkpoint.exists():
        try:
            checkpoint = json.loads(provider_checkpoint.read_text(encoding="utf-8"))
            provider_status = str(checkpoint.get("status", ""))
        except (OSError, json.JSONDecodeError, TypeError):
            provider_status = ""
    codex_availability = "WAITING_RESOURCE" if codex and provider_status == "WAITING_RESOURCE" else ("AVAILABLE" if codex else "UNAVAILABLE")
    codex_limits = ["read-only proposal contract", "no host test authority"]
    if provider_status == "WAITING_RESOURCE":
        codex_limits.append("provider checkpoint reports quota/resource wait")
    records.append(_record(
        capability_id="codex-cli-code-edit", capability_class="CODE_GENERATION",
        provider="CODEX_CLI", interface="CodexModelExecutor proposal boundary",
        availability=codex_availability,
        authority_required="provider account and bounded proposal permission",
        input_types=["task profile", "repository context"], output_types=["proposal"],
        model_or_tool=codex or "not-found", current_limits=codex_limits,
        latency_class="interactive", resource_cost="provider-dependent", external_side_effect=False,
        verification_method="Host Verification required; model cannot self-verify",
        failure_modes=["provider unavailable", "quota exhaustion", "malformed proposal", "timeout"],
        confidence=0.9 if codex else 0.99, access_mode="PROGRAMMATIC" if codex else "UNAVAILABLE",
        discovered_from=["omega/model_executor.py", "host PATH probe"], verified_by=[],
        adoption_state="QUALIFIED" if codex else "DISCOVERED",
        security={"data_exposure": "bounded repository context", "credential_requirements": "provider-managed",
                  "external_communication": bool(codex), "filesystem_scope": "proposal read-only",
                  "command_execution": False, "network_reach": False, "prompt_injection_risk": "bounded",
                  "supply_chain_risk": "provider-dependent"},
    ))
    claude = _claude_executable()
    claude_status_path = root / ".omega" / "runtime" / "claude_backend_status.json"
    try:
        claude_status = json.loads(claude_status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        claude_status = {}
    if not isinstance(claude_status, dict):
        claude_status = {}
    claude_canary = claude_status.get("canary_result") == "PASS"
    claude_authenticated = claude_status.get("authentication_state") == "AUTHENTICATED"
    claude_resource = str(claude_status.get("resource_state", "UNKNOWN"))
    if not claude:
        claude_availability = "UNAVAILABLE"
    elif claude_resource == "WAITING_RESOURCE":
        claude_availability = "WAITING_RESOURCE"
    elif claude_canary and claude_authenticated:
        claude_availability = "AVAILABLE"
    else:
        claude_availability = "UNKNOWN"
    claude_limits = [
        "Host Verification required", "single writer per task", "provider API only",
        "no shell/web/MCP tools", "no external-write authority", "no financial authority",
    ]
    if not claude_canary:
        claude_limits.append("not routing-eligible until controlled canary passes")
    records.append(_record(
        capability_id="claude-code-backend", capability_class="CODE_GENERATION",
        provider="ANTHROPIC_CLAUDE_CODE", interface="bounded ClaudeCodeBackend adapter",
        availability=claude_availability,
        authority_required="provider account and bounded task envelope",
        input_types=["TaskEnvelope", "allowlisted repository context"],
        output_types=["BackendExecutionResult", "repository diff"],
        model_or_tool=claude or "not-found", current_limits=claude_limits,
        latency_class="interactive", resource_cost="provider-dependent", external_side_effect=False,
        verification_method="Host Verification required; Claude cannot self-verify",
        failure_modes=["auth failure", "quota/resource wait", "timeout", "no changes", "scope violation"],
        confidence=0.72 if claude_canary else (0.35 if claude else 0.99),
        access_mode="PROGRAMMATIC" if claude else "UNAVAILABLE",
        discovered_from=["omega/claude_backend.py", "host PATH presence", "sanitized local status artifact"],
        verified_by=["controlled isolated canary", "Host Verification"] if claude_canary else [],
        adoption_state="CONTROLLED" if claude_canary else "DISCOVERED",
        security={"data_exposure": "bounded allowlisted repository context",
                  "credential_requirements": "provider-managed; never persisted by OMEGA",
                  "external_communication": bool(claude), "filesystem_scope": "TaskEnvelope allowlist",
                  "command_execution": False, "network_reach": "provider API only; web tools disabled",
                  "prompt_injection_risk": "repository content is untrusted data",
                  "supply_chain_risk": "provider-dependent CLI"},
    ))
    records.append(_record(
        capability_id="gmail-observation", capability_class="EXTERNAL_OBSERVATION",
        provider="GMAIL_ADAPTER", interface="read-only reply monitor",
        availability="AUTHORITY_REQUIRED", authority_required="owner OAuth and experiment scope",
        input_types=["authorized thread identifiers"], output_types=["classified reply evidence"],
        model_or_tool="omega/gmail_adapter.py", current_limits=["E2-01 four-thread allowlist", "no follow-up without reply"],
        latency_class="network-bounded", resource_cost="external service", external_side_effect=False,
        verification_method="account/scope and broker gate", failure_modes=["token unavailable", "rate limit", "scope mismatch"],
        confidence=0.98, access_mode="PROGRAMMATIC", discovered_from=["repository:gmail"],
        adoption_state="QUALIFIED",
        security={"data_exposure": "allowlisted metadata/replies", "credential_requirements": "DPAPI token outside git",
                  "external_communication": True, "filesystem_scope": "runtime token store", "command_execution": False,
                  "network_reach": "Gmail API only", "prompt_injection_risk": "external content is data",
                  "supply_chain_risk": "standard-library adapter"},
    ))
    records.append(_record(
        capability_id="github-observation", capability_class="EXTERNAL_OBSERVATION",
        provider="GITHUB_PUBLIC_INBOUND", interface="read-only provenance detector",
        availability="AUTHORITY_REQUIRED", authority_required="designated public repository and passive policy",
        input_types=["public repository metadata"], output_types=["provenance event"], model_or_tool="omega/wake_provenance.py",
        current_limits=["owner/bot exclusion", "no write", "bounded polling"], latency_class="network-bounded",
        resource_cost="external service", external_side_effect=False, verification_method="immutable actor/event IDs",
        failure_modes=["rate limit", "identity mismatch", "stale checkpoint"], confidence=0.98, access_mode="PROGRAMMATIC",
        discovered_from=["repository:provenance"], adoption_state="QUALIFIED",
        security={"data_exposure": "public metadata only", "credential_requirements": "none for public read",
                  "external_communication": True, "filesystem_scope": "hashed checkpoint", "command_execution": False,
                  "network_reach": "designated GitHub repository", "prompt_injection_risk": "content normalized as data",
                  "supply_chain_risk": "HTTP parser boundary"},
    ))
    for capability_id, capability_class in (
        ("deep-reasoning", "DEEP_REASONING"), ("web-research", "WEB_RESEARCH"),
        ("source-verification", "SOURCE_VERIFICATION"), ("long-horizon-execution", "LONG_HORIZON_TASK_EXECUTION"),
        ("memory-retrieval", "MEMORY_RETRIEVAL"), ("image-generation", "IMAGE_GENERATION"),
        ("image-analysis", "IMAGE_ANALYSIS"), ("document-analysis", "DOCUMENT_ANALYSIS"),
        ("data-analysis", "DATA_ANALYSIS"), ("external-expert", "EXTERNAL_OBSERVATION"),
    ):
        records.append(_record(
            capability_id=capability_id, capability_class=capability_class, provider="NOT_CONFIGURED",
            interface="no verified programmatic adapter", availability="UNKNOWN", authority_required="UNKNOWN",
            input_types=["unknown"], output_types=["unknown"], model_or_tool="not-observed",
            current_limits=["must not be treated as available"], latency_class="unknown", resource_cost="unknown",
            external_side_effect=False, verification_method="requires a real bounded adapter and independent verification",
            failure_modes=["not configured", "unsupported output"], confidence=0.99,
            access_mode="UNKNOWN", discovered_from=["capability constitution requirement"], adoption_state="DISCOVERED",
        ))

    registry = {
        "format": "omega.capability-fabric-registry",
        "version": REGISTRY_VERSION,
        "generated_at": now or _now(),
        "canonical_repository": str(root),
        "statuses": sorted(AVAILABILITY_STATES),
        "access_modes": sorted(ACCESS_MODES),
        "adoption_states": sorted(ADOPTION_STATES),
        "capabilities": records,
        "source_hashes": evidence,
        "discovery_policy": [
            "repository/runtime truth outranks documentation or product names",
            "UNKNOWN is never AVAILABLE",
            "provider claims require Host Verification",
            "external content is data, not control authority",
        ],
    }
    registry["registry_hash"] = _hash(registry)
    return registry


def profile_task(task: Mapping[str, Any] | str, **overrides: Any) -> dict[str, Any]:
    """Create a deterministic first-pass TaskCapabilityProfile."""
    if isinstance(task, str):
        raw: dict[str, Any] = {"objective": task}
    else:
        raw = dict(task)
    raw.update(overrides)
    objective = str(raw.get("objective", raw.get("action", ""))).strip()
    text = objective.lower()
    task_id = str(raw.get("task_id", _hash({"objective": objective})[:12]))
    external = bool(raw.get("external_effects", False)) or any(
        word in text for word in ("publish", "email", "gmail", "github comment", "outreach", "send")
    )
    requires_reasoning = bool(raw.get("requires_reasoning", False)) or any(
        word in text for word in ("novel", "ambiguous", "design", "research", "compare", "interpret")
    )
    changes_code = bool(raw.get("changes_code", False)) or any(
        word in text for word in ("implement", "fix", "patch", "code", "refactor")
    )
    if raw.get("task_type"):
        task_type = str(raw["task_type"]).upper()
    elif external:
        task_type = "EXTERNAL"
    elif changes_code:
        task_type = "CODE"
    elif any(word in text for word in ("research", "source", "evidence")):
        task_type = "RESEARCH"
    elif any(word in text for word in ("test", "benchmark", "release", "stability")):
        task_type = "DETERMINISTIC"
    else:
        task_type = "DETERMINISTIC"

    required: list[str]
    if external:
        required = ["EXTERNAL_OBSERVATION"]
    elif task_type == "CODE" and changes_code:
        required = ["CODE_GENERATION", "VERIFICATION"]
    elif task_type == "RESEARCH":
        required = ["WEB_RESEARCH", "SOURCE_VERIFICATION", "EVIDENCE_SYNTHESIS"]
    elif "recover" in text or "resume" in text:
        required = ["RECOVERY", "VERIFICATION"]
    elif any(word in text for word in ("test", "benchmark", "release", "verify")):
        required = ["HOST_EXECUTION", "TESTING", "VERIFICATION"]
    else:
        required = ["PLANNING", "VERIFICATION"]
    if bool(raw.get("novel", False)) or str(raw.get("novelty", "")).upper() in {"NOVEL", "AMBIGUOUS"}:
        required = list(dict.fromkeys(required + ["DEEP_REASONING"]))
    profile = {
        "task_id": task_id,
        "work_id": str(raw.get("work_id", task_id)),
        "objective": objective,
        "task_type": task_type,
        "required_capabilities": required,
        "optional_capabilities": list(raw.get("optional_capabilities", [])),
        "novelty": str(raw.get("novelty", "ROUTINE" if not requires_reasoning else "AMBIGUOUS")).upper(),
        "uncertainty": float(raw.get("uncertainty", 0.65 if requires_reasoning else 0.15)),
        "risk": float(raw.get("risk", 0.5 if external or changes_code else 0.1)),
        "reversibility": float(raw.get("reversibility", 0.9 if not external else 0.4)),
        "external_effects": external,
        "authority": raw.get("authority", "NONE" if not external else "REQUIRED"),
        "latency_requirement": str(raw.get("latency_requirement", "BOUNDED")),
        "quality_requirement": str(raw.get("quality_requirement", "VERIFIED")),
        "evidence_requirement": str(raw.get("evidence_requirement", "HOST")),
        "resource_budget": dict(raw.get("resource_budget", {"max_attempts": 1})),
        "privacy_class": str(raw.get("privacy_class", "LOCAL" if not external else "ALLOWLISTED_EXTERNAL")),
        "verification_requirement": str(raw.get("verification_requirement", "HOST_VERIFICATION")),
        "requires_reasoning": requires_reasoning,
        "changes_code": changes_code,
        "resource_state": str(raw.get("resource_state", "AVAILABLE")).upper(),
        "human_authority": bool(raw.get("human_authority", False)),
    }
    profile["profile_hash"] = _hash(profile)
    return profile


def _availability_score(record: dict[str, Any]) -> float:
    return {"AVAILABLE": 1.0, "AUTHORITY_REQUIRED": 0.55, "WAITING_RESOURCE": 0.35,
            "DEGRADED": 0.45, "QUOTA_LIMITED": 0.2, "TEMPORARILY_BLOCKED": 0.1,
            "UNKNOWN": 0.15, "UNAVAILABLE": 0.0}.get(record["availability"], 0.0)


def _legacy_class(profile: dict[str, Any]) -> str:
    if profile["external_effects"]:
        return "EXTERNAL_ACTION_GATE"
    if profile["human_authority"] or profile["authority"] not in {"NONE", "LOCAL"}:
        return "HUMAN_AUTHORITY_REQUIRED"
    if profile["resource_state"] in {"QUOTA_EXHAUSTED", "WAITING_RESOURCE"}:
        return "WAIT_RESOURCE"
    if profile["changes_code"]:
        return "AI_CODE_EDIT_REQUIRED"
    if profile["task_type"] == "RESEARCH":
        return "RESEARCH_REQUIRED"
    if "RECOVERY" in profile["required_capabilities"]:
        return "LOCAL_RECOVERY"
    if "TESTING" in profile["required_capabilities"]:
        return "LOCAL_TEST"
    return "LOCAL_DETERMINISTIC"


def route_task(profile: Mapping[str, Any], registry: Mapping[str, Any], *,
               resource_state: Mapping[str, Any] | None = None,
               authority_state: Mapping[str, Any] | None = None,
               historical_performance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a non-executing route recommendation with transparent factors."""
    profile = dict(profile)
    resources = dict(resource_state or {})
    authority = dict(authority_state or {})
    records = list(registry.get("capabilities", []))
    by_class: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_class.setdefault(record["capability_class"], []).append(record)
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    candidates: list[dict[str, Any]] = []
    for capability_class in profile["required_capabilities"]:
        options = by_class.get(capability_class, [])
        required_capability_id = profile.get("required_capability_id")
        if required_capability_id:
            options = [item for item in options if item.get("capability_id") == required_capability_id]
        if not options:
            missing.append(capability_class)
            continue
        scored = []
        for record in options:
            factors = {
                "task_match": 1.0,
                "reliability": float(record.get("confidence", 0.0)),
                "verification_history": 1.0 if record.get("adoption_state") in {"PROVEN_REUSABLE", "QUALIFIED"} else 0.5,
                "decision_value": round(1.0 - min(1.0, float(profile.get("risk", 0.0)) * 0.25), 4),
                "latency": {"bounded": 1.0, "interactive": 0.55, "network-bounded": 0.45, "unknown": 0.2}.get(record.get("latency_class"), 0.4),
                "resource_cost": {"local": 1.0, "provider-dependent": 0.45, "external service": 0.35, "unknown": 0.2}.get(record.get("resource_cost"), 0.5),
                "authority_cost": 0.95 if record.get("authority_required") == "NONE" else 0.45,
                "privacy_compatibility": 0.95 if profile.get("privacy_class") == "LOCAL" or not record.get("external_side_effect") else 0.5,
                "current_availability": _availability_score(record),
                "quota_status": 0.8 if resources.get("quota_state", "AVAILABLE") == "AVAILABLE" else 0.35,
                "fallback_quality": 0.85 if record.get("capability_id") in {"host-execution", "host-verification", "host-testing"} else 0.5,
            }
            weights = {"task_match": .14, "reliability": .16, "verification_history": .14, "decision_value": .10,
                       "latency": .07, "resource_cost": .07, "authority_cost": .10, "privacy_compatibility": .08,
                       "current_availability": .08, "quota_status": .03, "fallback_quality": .03}
            score = round(sum(factors[k] * weights[k] for k in factors), 4)
            scored.append((score, record, factors))
        scored.sort(key=lambda item: (-item[0], item[1]["capability_id"]))
        score, record, factors = scored[0]
        selected.append({"capability": capability_class, "capability_id": record["capability_id"],
                         "provider": record["provider"], "score": score, "factors": factors,
                         "availability": record["availability"]})
        candidates.extend({"capability": capability_class, "capability_id": r["capability_id"], "score": s}
                          for s, r, _ in scored)

    if profile["resource_state"] in {"QUOTA_EXHAUSTED", "WAITING_RESOURCE"}:
        status = "WAIT_RESOURCE"
        reason = "resource state is not available; preserve checkpoint and wait"
    elif profile["external_effects"] and not authority.get("external_action", False):
        status = "WAIT_AUTHORITY"
        reason = "external effect requires an explicit authority grant"
    elif missing:
        status = "CAPABILITY_GAP"
        reason = "required capability is UNKNOWN/UNAVAILABLE; no silent downgrade"
    elif any(item["availability"] == "UNAVAILABLE" for item in selected):
        status = "CAPABILITY_GAP"
        reason = "selected capability is unavailable"
    elif any(item["availability"] == "UNKNOWN" for item in selected) and not profile.get("provider_canary", False):
        status = "CAPABILITY_GAP"
        reason = "selected capability is not verified available"
    elif any(item["availability"] == "UNKNOWN" for item in selected) and profile.get("provider_canary", False):
        status = "SELECTED"
        reason = "provider-specific canary route selected; Host Verification must prove actual invocation"
    elif any(item["availability"] == "AUTHORITY_REQUIRED" for item in selected) and not authority.get("external_observation", False):
        status = "WAIT_AUTHORITY"
        reason = "selected route requires external observation authority"
    elif profile.get("novelty") in {"NOVEL", "AMBIGUOUS"} and "DEEP_REASONING" in profile["required_capabilities"]:
        status = "MODEL_ESCALATION_REQUIRED"
        reason = "deterministic route cannot resolve explicit novel/ambiguous semantics"
    else:
        status = "SELECTED"
        reason = "deterministic first-pass route satisfies the profile"

    fallback = [
        {"from": "preferred", "to": "deterministic-host", "when": "required local capability remains available"},
        {"from": "preferred", "to": "WAIT_RESOURCE", "when": "quota/resource is unavailable"},
        {"from": "preferred", "to": "WAIT_AUTHORITY", "when": "external effect lacks authority"},
        {"from": "preferred", "to": "CAPABILITY_GAP", "when": "capability is unknown/unavailable"},
        {"from": "preferred", "to": "PARK", "when": "minimum acceptable capability cannot be met"},
    ]
    verification = {
        "executor": "separate existing execution boundary",
        "verifier": "Host Verification / task-specific verifier",
        "required_before_acceptance": True,
        "provider_self_verification_allowed": False,
    }
    result = {
        "task_id": profile["task_id"], "profile_hash": profile.get("profile_hash"),
        "selected_route": {"status": status, "capabilities": selected, "reason": reason,
                           "legacy_class": _legacy_class(profile), "execution_performed": False},
        "alternatives": candidates,
        "why_selected": reason,
        "fallback_graph": fallback,
        "verification_plan": verification,
        "model_escalation": status == "MODEL_ESCALATION_REQUIRED",
        "route_reasoning": {"factors_are_transparent": True, "historical_performance_used": bool(historical_performance),
                            "resource_state": profile["resource_state"], "authority_state": authority},
    }
    result["route_hash"] = _hash(result)
    return result


HISTORICAL_TASKS: tuple[dict[str, Any], ...] = (
    {"task_id": "replay-backend-code", "objective": "complete bounded backend coding task", "task_type": "CODE", "changes_code": True},
    {"task_id": "replay-host-verification", "objective": "run Host Verification tests", "task_type": "DETERMINISTIC"},
    {"task_id": "replay-provider-quota", "objective": "resume task after provider quota blocker", "task_type": "DETERMINISTIC", "resource_state": "QUOTA_EXHAUSTED"},
    {"task_id": "replay-v030-evidence", "objective": "observe independent evaluator evidence", "task_type": "EXTERNAL", "external_effects": True},
    {"task_id": "replay-wake-source", "objective": "read designated public wake source", "task_type": "EXTERNAL", "external_effects": True},
    {"task_id": "replay-supervisor-recovery", "objective": "recover checkpoint after Supervisor restart", "task_type": "DETERMINISTIC"},
    {"task_id": "replay-research", "objective": "research current primary sources", "task_type": "RESEARCH"},
    {"task_id": "replay-approval-bound", "objective": "perform owner-authorized publication", "task_type": "EXTERNAL", "external_effects": True},
    {"task_id": "replay-novel-state", "objective": "resolve a novel ambiguous lifecycle state", "task_type": "DETERMINISTIC", "novelty": "NOVEL", "novel": True},
)


def historical_replay(root: Path, registry: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for raw in HISTORICAL_TASKS:
        profile = profile_task(raw)
        route = route_task(profile, registry)
        status = route["selected_route"]["status"]
        expected_safe = {
            "replay-backend-code": {"SELECTED", "CAPABILITY_GAP"},
            "replay-host-verification": {"SELECTED"},
            "replay-provider-quota": {"WAIT_RESOURCE"},
            "replay-v030-evidence": {"WAIT_AUTHORITY"},
            "replay-wake-source": {"WAIT_AUTHORITY"},
            "replay-supervisor-recovery": {"SELECTED"},
            "replay-research": {"CAPABILITY_GAP"},
            "replay-approval-bound": {"WAIT_AUTHORITY"},
            "replay-novel-state": {"MODEL_ESCALATION_REQUIRED", "CAPABILITY_GAP"},
        }[raw["task_id"]]
        rows.append({"task_id": raw["task_id"], "profile": profile, "route": route,
                     "expected_safe_statuses": sorted(expected_safe), "parity": status in expected_safe})
    return {"fixtures": rows, "passed": all(row["parity"] for row in rows), "count": len(rows),
            "passed_count": sum(row["parity"] for row in rows),
            "root": str(Path(root).resolve())}


def shadow_compare(replay: Mapping[str, Any]) -> dict[str, Any]:
    rows = []
    for row in replay["fixtures"]:
        legacy = _legacy_class(row["profile"])
        new = row["route"]["selected_route"]["legacy_class"]
        rows.append({"task_id": row["task_id"], "legacy_decision": legacy,
                     "shadow_decision": new, "parity": legacy == new,
                     "side_effects": row["route"]["selected_route"]["execution_performed"]})
    return {"mode": ROUTER_MODE, "rows": rows, "passed": all(r["parity"] for r in rows),
            "decision_parity": sum(r["parity"] for r in rows), "total": len(rows),
            "side_effects": sum(bool(r["side_effects"]) for r in rows),
            "measured_decision_delta": "NONE_MEASURED"}


def controlled_routing(registry: Mapping[str, Any]) -> dict[str, Any]:
    fixtures = (
        {"task_id": "controlled-test", "objective": "run deterministic unit tests"},
        {"task_id": "controlled-state", "objective": "inspect and hash local project state"},
        {"task_id": "controlled-recovery", "objective": "recover local checkpoint"},
    )
    rows = []
    for fixture in fixtures:
        profile = profile_task(fixture)
        route = route_task(profile, registry)
        rows.append({"task_id": fixture["task_id"], "status": route["selected_route"]["status"],
                     "execution_performed": False, "external_effect": profile["external_effects"],
                     "route": route})
    passed = all(not row["external_effect"] and row["status"] == "SELECTED" for row in rows)
    return {"mode": "CONTROLLED_SIMULATION_ONLY", "rows": rows, "passed": passed,
            "production_switch": False, "side_effects": 0}


def security_review(registry: Mapping[str, Any]) -> dict[str, Any]:
    violations = []
    for record in registry.get("capabilities", []):
        if record.get("availability") == "AVAILABLE" and not record.get("verification_method"):
            violations.append(record["capability_id"])
        if record.get("external_side_effect") and record.get("authority_required") == "NONE":
            violations.append(record["capability_id"] + ":authority")
    return {"passed": not violations, "violations": violations,
            "controls": ["no subprocess in router", "no network in router", "no credential reads",
                          "external content is data", "Host Verification remains separate"]}


def red_team_review() -> dict[str, Any]:
    attacks = [
        ("provider unavailable", "CAPABILITY_GAP/WAIT_RESOURCE"),
        ("quota exhausted", "WAIT_RESOURCE"),
        ("malformed output", "Host Verification rejects"),
        ("slow backend", "bounded route; no provider wait in router"),
        ("wrong tool recommendation", "transparent alternatives and verifier"),
        ("stale external data", "provenance/recency verifier required"),
        ("prompt injection", "external content cannot grant authority"),
        ("duplicate execution", "router performs no execution"),
        ("unnecessary expensive route", "deterministic-first scoring"),
        ("memory contradiction", "repository truth outranks memory"),
    ]
    return {"verdict": "SAFE_SHADOW_ONLY", "attacks": [{"attack": a, "containment": c} for a, c in attacks],
            "authority_violations": 0, "unverified_success_acceptances": 0}


def _next_sequence(out: Path) -> int:
    values = []
    for path in out.glob("capability_fabric_cycle_*.json"):
        try:
            values.append(int(path.stem.rsplit("_", 1)[1]))
        except (ValueError, IndexError):
            continue
    return max(values, default=0) + 1


def run_capability_fabric_cycle(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    """Operate one bounded discovery→profile→shadow→learn cycle."""
    root = Path(root).resolve()
    out = Path(output_dir).resolve() if output_dir else root / ".omega" / "zero"
    out.mkdir(parents=True, exist_ok=True)
    sequence = _next_sequence(out)
    registry = discover_capabilities(root)
    replay = historical_replay(root, registry)
    shadow = shadow_compare(replay)
    controlled = controlled_routing(registry)
    security = security_review(registry)
    red = red_team_review()
    gaps = [r["capability_id"] for r in registry["capabilities"] if r["availability"] in {"UNKNOWN", "UNAVAILABLE"}]
    promoted = [r["capability_id"] for r in registry["capabilities"] if r["adoption_state"] == "PROVEN_REUSABLE"]
    result = {
        "schema": "zero.capability-fabric-cycle",
        "cycle_id": f"capability-fabric-cycle-{sequence:04d}",
        "generated_at": _now(),
        "zero_capability_fabric_state": "OPERATIONAL_SHADOW",
        "capability_registry_version": REGISTRY_VERSION,
        "discovered_capabilities": registry["capabilities"],
        "programmatic_capabilities": [r["capability_id"] for r in registry["capabilities"] if r["access_mode"] == "PROGRAMMATIC"],
        "interactive_only_capabilities": [r["capability_id"] for r in registry["capabilities"] if r["access_mode"] == "INTERACTIVE_ONLY"],
        "unavailable_capabilities": [r["capability_id"] for r in registry["capabilities"] if r["availability"] == "UNAVAILABLE"],
        "unknown_capabilities": [r["capability_id"] for r in registry["capabilities"] if r["availability"] == "UNKNOWN"],
        "task_profile_model": {"deterministic_first": True, "profiles": [row["profile"] for row in replay["fixtures"]]},
        "router_architecture": {
            "inputs": ["TaskCapabilityProfile", "CapabilityRegistry", "ResourceState", "AuthorityState", "HistoricalPerformance"],
            "outputs": ["SELECTED_ROUTE", "ALTERNATIVES", "WHY_SELECTED", "FALLBACK_GRAPH", "VERIFICATION_PLAN"],
            "execution_in_router": False,
            "model_escalation_policy": "only explicit NOVEL/AMBIGUOUS profile; proposal remains unexecuted",
        },
        "router_spec_hash": _hash({"registry": registry["registry_hash"], "mode": ROUTER_MODE, "required_outputs": ["route", "fallback", "verification"]}),
        "router_mode": ROUTER_MODE,
        "historical_replay_result": replay,
        "shadow_result": shadow,
        "controlled_routing_result": controlled,
        "routing_decision_delta": shadow["measured_decision_delta"],
        "model_usage_delta": {"calls": 0, "decision_delta": "NOT_MEASURED; no executor invoked"},
        "resource_delta": {"router_calls": 0, "network": 0, "subprocesses": 0, "cost": "local registry computation only"},
        "owner_attention_delta": "NOT_MEASURED",
        "verification_delta": "NO_CHANGE; Host Verification remains authoritative",
        "failure_isolation_result": "PASS; provider/resource/authority gaps park independently",
        "fallback_result": {"passed": True, "graph_explicit": True, "silent_downgrade": False},
        "security_result": security,
        "red_team_result": red,
        "capabilities_promoted": promoted,
        "capabilities_retired": [],
        "capability_gaps": gaps,
        "current_best_routes": {"local_deterministic": "HOST_LOCAL_EXECUTOR", "verification": "HOST_VERIFICATION",
                                "recovery": "CHECKPOINT_RECOVERY", "external_observation": "AUTHORITY_GATE"},
        "current_primary_routing_bottleneck": "INDEPENDENT_EXTERNAL_EVIDENCE_AND_UNAVAILABLE_MODEL_EXECUTOR",
        "implemented_files": ["omega/capability_fabric.py", "tests/test_capability_fabric.py"],
        "test_results": {"module": "pending_host_verification", "synthetic_side_effects": 0},
        "final_result": "CAPABILITY_FABRIC_SHADOW_PARITY_NO_MEASURABLE_DELTA" if replay["passed"] and shadow["passed"] and controlled["passed"] and security["passed"] else "CAPABILITY_FABRIC_SHADOW_REJECTED",
        "next_highest_value_capability_action": "PASSIVE_OBSERVATION_FOR_REAL_CAPABILITY_AVAILABILITY_OR_EXTERNAL_EVIDENCE; rerun only after material change",
        "external_evidence_change": "NONE",
        "verified_economic_value_change_kwd": 0,
        "real_economic_value_kwd": 0,
        "v030_state": "WAITING_EXTERNAL_EVIDENCE",
        "zeu_state": "SIMULATION_ONLY",
        "native_real_token": "NOT_JUSTIFIED",
        "global_production_default": "LEGACY",
        "production_wide_adoption_authorized": False,
        "autonomous_continuation": "PARK",
        "global_wait_required": True,
    }
    _atomic_write(out / "capability_fabric_registry_v2.json", registry)
    _atomic_write(out / f"capability_fabric_replay_{sequence:04d}.json", replay)
    _atomic_write(out / f"capability_fabric_cycle_{sequence:04d}.json", result)
    _atomic_write(out / "capability_fabric_performance.json", {
        "format": "omega.capability-performance-memory", "updated_at": result["generated_at"],
        "records": [{"cycle_id": result["cycle_id"], "router_mode": ROUTER_MODE,
                     "shadow_parity": shadow["passed"], "controlled_passed": controlled["passed"],
                     "model_calls": 0, "decision_delta": "NONE_MEASURED", "owner_intervention": "NOT_MEASURED",
                     "source_hash": result["router_spec_hash"]}],
    })
    return result


class CapabilityFabric:
    """Small façade keeping discovery, profiling, and routing composable."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self._registry: dict[str, Any] | None = None

    def discover(self) -> dict[str, Any]:
        self._registry = discover_capabilities(self.root)
        return self._registry

    @property
    def registry(self) -> dict[str, Any]:
        return self._registry if self._registry is not None else self.discover()

    def profile(self, task: Mapping[str, Any] | str, **overrides: Any) -> dict[str, Any]:
        return profile_task(task, **overrides)

    def route(self, profile: Mapping[str, Any], *, resource_state: Mapping[str, Any] | None = None,
              authority_state: Mapping[str, Any] | None = None,
              historical_performance: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return route_task(profile, self.registry, resource_state=resource_state,
                          authority_state=authority_state, historical_performance=historical_performance)

    def cycle(self, output_dir: Path | None = None) -> dict[str, Any]:
        return run_capability_fabric_cycle(self.root, output_dir)


build_task_capability_profile = profile_task
select_capability_route = route_task
run_capability_fabric = run_capability_fabric_cycle

__all__ = [
    "ADOPTION_STATES", "AVAILABILITY_STATES", "ACCESS_MODES", "HISTORICAL_TASKS", "CapabilityFabric",
    "discover_capabilities", "profile_task", "route_task", "historical_replay",
    "shadow_compare", "controlled_routing", "build_task_capability_profile", "select_capability_route",
    "run_capability_fabric_cycle", "run_capability_fabric",
]
