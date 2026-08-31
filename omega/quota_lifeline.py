"""Thin coordination layer for provider quota/resource waits.

This module reuses existing OMEGA components instead of duplicating lifecycle
logic. It parks the same task on quota/resource blockers, records a read-only
safe checkpoint, requires an exact retry timestamp when one is claimed, allows
at most one bounded availability probe per wake, and rehydrates the same task
after a verified wake.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .capability_fabric import discover_capabilities
from .provider_resilience import checkpoint_task, schedule_quota_wait
from .task_continuity import ContinuityEngine, ReconciliationError, TaskContinuityStore, classify_blocker
from .wake_plane import status as wake_plane_status
from .zfbr import block, classify, freeze, resume

WAIT_ROOT = Path(".omega") / "runtime" / "quota_lifeline"
WAIT_BLOCKERS = {"USAGE_QUOTA_LIMIT", "WAITING_RESOURCE", "QUOTA_EXHAUSTED"}
USAGE_WINDOW_STATES = {"AVAILABLE", "EXHAUSTED", "UNKNOWN"}
USAGE_SOURCES = {"CODEX_CLI_STATUS", "CODEX_USAGE_DASHBOARD"}


def _store(root: Path) -> TaskContinuityStore:
    return TaskContinuityStore(root / ".omega" / "runtime" / "task_continuity")


def _engine(root: Path) -> ContinuityEngine:
    return ContinuityEngine(_store(root))


def _lifeline_path(root: Path, task_id: str) -> Path:
    return root / WAIT_ROOT / f"{task_id}.json"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _require_iso8601(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("retry timestamp must include timezone offset")
    return value


def _usage_window(state: str, reset_at: str | None) -> dict[str, Any]:
    if state not in USAGE_WINDOW_STATES:
        raise ValueError(f"unsupported Codex usage window state: {state}")
    if reset_at is not None:
        reset_at = _require_iso8601(reset_at)
    if state == "EXHAUSTED" and reset_at is None:
        raise ValueError("an exhausted Codex usage window requires a verified reset timestamp")
    if state != "EXHAUSTED" and reset_at is not None:
        raise ValueError("a reset timestamp is allowed only for an exhausted usage window")
    return {"state": state, "reset_at": reset_at, "verified_reset_timestamp": bool(reset_at)}


def _resource_wait_route(root: Path) -> str:
    registry = discover_capabilities(root)
    capabilities = registry.get("capabilities", [])
    codex = next((item for item in capabilities if item.get("capability_id") == "codex-cli-code-edit"), {})
    return str(codex.get("availability", "UNKNOWN"))


def park_for_resource_wait(
    root: Path,
    *,
    task_id: str,
    task_class: str,
    objective: str,
    session_id: str,
    repository_root: Path,
    completed_steps: list[str],
    next_action: str,
    authority_envelope_id: str | None = None,
    authority_status: str = "ACTIVE",
    backend: str = "CODEX_BACKEND",
    retry_at: str | None = None,
    blocker: str = "USAGE_QUOTA_LIMIT",
    frozen_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    repository_root = Path(repository_root).resolve()
    blocker_class = classify_blocker(blocker)
    if blocker_class not in {"USAGE_QUOTA_LIMIT", "UNKNOWN_BLOCKER"} and blocker not in WAIT_BLOCKERS:
        raise ValueError("park_for_resource_wait only supports quota/resource blockers")
    if retry_at is not None:
        retry_at = _require_iso8601(retry_at)

    engine = _engine(root)
    task = engine.accept(task_id, task_class, objective, authority_envelope_id=authority_envelope_id, authority_status=authority_status)
    if task.backend is None:
        engine.route(task_id, backend)
    if task.active_session_id is None:
        engine.start_session(task_id, backend, session_id=session_id)
    elif task.active_session_id != session_id:
        raise ReconciliationError("quota park must preserve the current task owner session")

    checkpoint = engine.checkpoint(task_id, session_id, completed_steps=completed_steps, next_action=next_action, repository_root=repository_root)
    parked = engine.lose_session(task_id, session_id, blocker_class)
    frozen = freeze(task_id, "PROVIDER_WAIT", frozen_spec or {
        "task_id": task_id,
        "objective": objective,
        "backend": backend,
        "next_action": next_action,
        "read_only_safe_mode": True,
    }, authority=["same durable task"], resources=["provider recovery"])
    frozen = block(frozen, classify("PROVIDER_FAILURE", resource="QUOTA", summary="provider quota/resource wait; no bypass or rotation"))
    frozen = resume(frozen, blocker_resolved=False, resources_valid=False)

    preb_task = {
        "task_id": task_id,
        "branch": "quota-lifeline",
        "frozen_inputs": [str(repository_root)],
        "repository_baseline": "checkpointed",
        "files_modified": [],
        "expected_outputs": [next_action],
        "tests_completed": [],
        "remaining_work": [next_action],
        "evidence_hashes": [checkpoint.integrity_hash],
    }
    preb = schedule_quota_wait(root, preb_task, retry_at) if retry_at else {
        "checkpoint": checkpoint_task(root, preb_task, reason=blocker_class, backend_used=backend, next_retry_at=None),
        "wake": {"state": "WAITING_RESOURCE", "wake_condition": "PROVIDER_RECOVERY", "next_retry_at": None, "probe_policy": "exactly one bounded availability probe after verified wake", "retry_storm": False},
    }

    record = {
        "task_id": task_id,
        "backend": backend,
        "state": "WAITING_RESOURCE",
        "read_only_safe_mode": True,
        "retry_at": retry_at,
        "verified_retry_timestamp": bool(retry_at),
        "probe_count": 0,
        "probe_limit": 1,
        "material_wake_seen": False,
        "material_wake": None,
        "same_task_required": True,
        "provider_rotation": False,
        "production_routing_changed": False,
        "task_continuity_status": engine.status(task_id),
        "zfbr": {"state": frozen.state, "blocker_class": frozen.blocker_class, "resume_condition": frozen.resume_condition},
        "preb": preb,
        "wake_plane": wake_plane_status(root),
        "resource_route_availability": _resource_wait_route(root),
    }
    _write_json(_lifeline_path(root, task_id), record)
    return record


def record_material_wake(root: Path, *, task_id: str, trigger: str, source: str, wake_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    path = _lifeline_path(root, task_id)
    record = _read_json(path, None)
    if not isinstance(record, dict):
        raise FileNotFoundError(f"no quota lifeline record for task: {task_id}")
    store = _store(root)
    task = store.load_task(task_id)
    if task.state == "PARKED" and task.blocker_class in {"USAGE_QUOTA_LIMIT", "UNKNOWN_BLOCKER"}:
        task.state = "BACKEND_ROUTED" if task.backend else "TASK_ACCEPTED"
        task.recovery_state = "MATERIAL_WAKE_ACCEPTED"
        task.next_trigger = None
        store.save_task(task, expected_revision=task.revision)
        store.event("MATERIAL_WAKE_ACCEPTED", task_id=task_id, trigger=trigger, source=source)
    record["material_wake_seen"] = True
    record["material_wake"] = {"trigger": trigger, "source": source, "payload": wake_payload or {}}
    record["probe_count"] = 0
    _write_json(path, record)
    return record


def bounded_probe(root: Path, *, task_id: str, provider_available: bool, observed_at: str | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    path = _lifeline_path(root, task_id)
    record = _read_json(path, None)
    if not isinstance(record, dict):
        raise FileNotFoundError(f"no quota lifeline record for task: {task_id}")
    if not record.get("material_wake_seen"):
        raise ReconciliationError("bounded probe requires a prior material wake")
    if int(record.get("probe_count", 0)) >= int(record.get("probe_limit", 1)):
        raise ReconciliationError("bounded probe already consumed for this wake")
    record["probe_count"] = int(record.get("probe_count", 0)) + 1
    record["last_probe"] = {
        "observed_at": observed_at,
        "provider_available": bool(provider_available),
        "bounded": True,
    }
    if provider_available:
        record["state"] = "PROBE_SUCCEEDED"
    _write_json(path, record)
    return record


def record_codex_usage_snapshot(
    root: Path,
    *,
    task_id: str,
    source: str,
    observed_at: str,
    five_hour_state: str,
    weekly_state: str,
    five_hour_reset_at: str | None = None,
    weekly_reset_at: str | None = None,
) -> dict[str, Any]:
    """Attach a human-visible Codex usage snapshot without querying private APIs.

    Codex exposes usage in its UI and CLI status, not through an application API
    available to OMEGA.  This records only an explicitly observed snapshot and
    never estimates usage, consumes a reset, or attempts a provider bypass.
    """
    root = Path(root).resolve()
    if source not in USAGE_SOURCES:
        raise ValueError("usage snapshot source must be CODEX_CLI_STATUS or CODEX_USAGE_DASHBOARD")
    observed_at = _require_iso8601(observed_at)
    path = _lifeline_path(root, task_id)
    record = _read_json(path, None)
    if not isinstance(record, dict):
        raise FileNotFoundError(f"no quota lifeline record for task: {task_id}")

    five_hour = _usage_window(five_hour_state, five_hour_reset_at)
    weekly = _usage_window(weekly_state, weekly_reset_at)
    exhausted_resets = [
        (datetime.fromisoformat(window["reset_at"]), window["reset_at"])
        for window in (five_hour, weekly)
        if window["state"] == "EXHAUSTED"
    ]
    record["codex_usage"] = {
        "source": source,
        "observed_at": observed_at,
        "five_hour": five_hour,
        "weekly": weekly,
        "usable": five_hour["state"] == "AVAILABLE" and weekly["state"] == "AVAILABLE",
        "next_retry_at": max(exhausted_resets, key=lambda item: item[0])[1] if exhausted_resets else None,
        "estimated": False,
        "reset_consumed": False,
        "provider_rotation": False,
    }
    _write_json(path, record)
    return record


def manually_rearm_after_usage_refresh(
    root: Path,
    *,
    task_id: str,
    source: str,
    observed_at: str,
) -> dict[str, Any]:
    """Record an owner-observed quota refresh and permit one normal probe.

    This does not restart Codex, consume a reset, or alter its account limits.
    It is intentionally manual because OMEGA has no authority to read or change
    a Codex account's usage allowance.
    """
    record_codex_usage_snapshot(
        root,
        task_id=task_id,
        source=source,
        observed_at=observed_at,
        five_hour_state="AVAILABLE",
        weekly_state="AVAILABLE",
    )
    return record_material_wake(
        root,
        task_id=task_id,
        trigger="MANUAL_CODEX_USAGE_REFRESH",
        source=source,
        wake_payload={"observed_at": observed_at, "owner_confirmed": True},
    )


def rehydrate_same_task(
    root: Path,
    *,
    task_id: str,
    session_id: str,
    repository_root: Path,
    authority_envelope_id: str | None,
    authority_status: str = "ACTIVE",
    backend: str = "CODEX_BACKEND",
) -> dict[str, Any]:
    root = Path(root).resolve()
    repository_root = Path(repository_root).resolve()
    path = _lifeline_path(root, task_id)
    record = _read_json(path, None)
    if not isinstance(record, dict):
        raise FileNotFoundError(f"no quota lifeline record for task: {task_id}")
    if not record.get("material_wake_seen"):
        raise ReconciliationError("cannot rehydrate before material wake")
    last_probe = record.get("last_probe") or {}
    if not last_probe.get("provider_available"):
        raise ReconciliationError("cannot rehydrate before a successful bounded probe")
    if record.get("backend") != backend:
        raise ReconciliationError("backend rotation is not allowed for quota lifeline rehydration")

    engine = _engine(root)
    engine.start_session(task_id, backend, session_id=session_id)
    checkpoint = engine.rehydrate(task_id, session_id, repository_root, authority_envelope_id=authority_envelope_id, authority_status=authority_status)
    resumed = engine.resume(task_id, session_id)
    record["state"] = "TASK_RESUMED"
    record["task_continuity_status"] = engine.status(task_id)
    record["rehydrated_checkpoint_id"] = checkpoint.checkpoint_id
    record["session_id"] = session_id
    record["resumed_state"] = resumed.state
    _write_json(path, record)
    return record


def quota_lifeline_status(root: Path, task_id: str) -> dict[str, Any]:
    root = Path(root).resolve()
    record = _read_json(_lifeline_path(root, task_id), {})
    if not isinstance(record, dict):
        return {}
    return record


__all__ = [
    "bounded_probe",
    "manually_rearm_after_usage_refresh",
    "park_for_resource_wait",
    "quota_lifeline_status",
    "record_codex_usage_snapshot",
    "record_material_wake",
    "rehydrate_same_task",
]
