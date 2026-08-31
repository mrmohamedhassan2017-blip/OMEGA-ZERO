from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "ZERO_CONSTITUTIONAL_EXPERIMENT_MODE"
ALLOWED_CLASSES = ("A0_READ", "A1_INTERNAL_EXECUTION", "A2_INTERNAL_PREPARATION")
BLOCKED_CLASSES = (
    "EXTERNAL_WRITE",
    "FINANCIAL_ACTION",
    "SECURITY_TESTING",
    "ACCOUNT_MUTATION",
    "UNKNOWN_ACTION",
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _base(root: Path) -> Path:
    return Path(root).resolve() / ".omega" / "zero" / "experiment"


def _state_path(root: Path) -> Path:
    return _base(root) / "state.json"


def _events_path(root: Path) -> Path:
    return _base(root) / "events.jsonl"


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _event(root: Path, kind: str, **data: Any) -> dict[str, Any]:
    record = {"timestamp": _now(), "event": kind, **data}
    path = _events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed.pop("activation_hash", None)
    sealed["activation_hash"] = _hash(sealed)
    return sealed


def read_experiment_state(root: Path) -> dict[str, Any]:
    path = _state_path(root)
    if not path.exists():
        return {
            "experiment_id": EXPERIMENT_ID,
            "enabled": False,
            "state": "DISABLED",
            "allowed_classes": list(ALLOWED_CLASSES),
            "blocked_classes": list(BLOCKED_CLASSES),
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"experiment_id": EXPERIMENT_ID, "enabled": False, "state": "CORRUPT_FAIL_CLOSED"}
    if not isinstance(value, dict):
        return {"experiment_id": EXPERIMENT_ID, "enabled": False, "state": "CORRUPT_FAIL_CLOSED"}
    check = dict(value)
    expected = check.pop("activation_hash", None)
    if value.get("enabled") and expected != _hash(check):
        return {"experiment_id": EXPERIMENT_ID, "enabled": False, "state": "HASH_MISMATCH_FAIL_CLOSED"}
    expires_at = _parse_time(value.get("expires_at"))
    if value.get("enabled") and expires_at and datetime.now(expires_at.tzinfo or timezone.utc).astimezone() > expires_at:
        value["enabled"] = False
        value["state"] = "EXPIRED_FAIL_CLOSED"
    return value


def enable_experiment_override(root: Path, *, task_id: str | None = None,
                               reason: str = "temporary internal experiment",
                               max_runtime_minutes: int = 120) -> dict[str, Any]:
    started = datetime.now(timezone.utc).astimezone()
    state = {
        "experiment_id": EXPERIMENT_ID,
        "enabled": True,
        "state": "ACTIVE",
        "started_at": started.isoformat(timespec="seconds"),
        "expires_at": (started + timedelta(minutes=max_runtime_minutes)).isoformat(timespec="seconds"),
        "scope": "A0_READ_A1_INTERNAL_EXECUTION_A2_INTERNAL_PREPARATION_ONLY",
        "task_id": task_id,
        "authority_before": "AUTH_REQUIRED/WAIT_AUTH",
        "authority_during": "EXPERIMENT_AUTHORIZED",
        "allowed_classes": list(ALLOWED_CLASSES),
        "blocked_classes": list(BLOCKED_CLASSES),
        "activation_reason": reason,
        "external_writes": 0,
        "financial_actions": 0,
        "security_actions": 0,
        "production_routing_changed": False,
    }
    state = _seal(state)
    _atomic_write(_state_path(root), state)
    _event(root, "EXPERIMENT_OVERRIDE_ACTIVATED", task_id=task_id, authority_source="EXPERIMENT_OVERRIDE")
    return state


def disable_experiment_override(root: Path, *, reason: str = "manual restore") -> dict[str, Any]:
    previous = read_experiment_state(root)
    state = {
        "experiment_id": EXPERIMENT_ID,
        "enabled": False,
        "state": "DISABLED",
        "disabled_at": _now(),
        "restore_behavior": "NORMAL_CONSTITUTIONAL_AUTHORITY_RULES",
        "reason": reason,
        "previous_activation_hash": previous.get("activation_hash"),
        "allowed_classes": list(ALLOWED_CLASSES),
        "blocked_classes": list(BLOCKED_CLASSES),
    }
    _atomic_write(_state_path(root), state)
    _event(root, "EXPERIMENT_OVERRIDE_DISABLED", reason=reason)
    return state


def classify_action(action: str | None) -> str:
    text = (action or "").lower()
    if not text.strip():
        return "UNKNOWN_ACTION"
    if any(token in text for token in ("pay", "purchase", "withdraw", "transfer money", "invoice", "bank", "crypto")):
        return "FINANCIAL_ACTION"
    if any(token in text for token in ("send email", "post comment", "publish", "push github", "external write", "message ")):
        return "EXTERNAL_WRITE"
    if any(token in text for token in ("exploit", "scan target", "security test", "attack", "pentest")):
        return "SECURITY_TESTING"
    if any(token in text for token in ("inspect", "status", "read", "verify state")):
        return "A0_READ"
    if any(token in text for token in ("test", "benchmark", "execute", "run", "repair", "host verification")):
        return "A1_INTERNAL_EXECUTION"
    if any(token in text for token in ("prepare", "draft", "plan", "create mission", "checkpoint", "learn")):
        return "A2_INTERNAL_PREPARATION"
    return "UNKNOWN_ACTION"


def evaluate_experiment_authority(root: Path, *, action: str, task_id: str | None = None) -> dict[str, Any]:
    state = read_experiment_state(root)
    action_class = classify_action(action)
    allowed = bool(state.get("enabled")) and action_class in ALLOWED_CLASSES
    result = {
        "experiment_id": EXPERIMENT_ID,
        "enabled": bool(state.get("enabled")),
        "task_id": task_id or state.get("task_id"),
        "action": action,
        "action_class": action_class,
        "authority_source": "EXPERIMENT_OVERRIDE" if allowed else "NORMAL_AUTHORITY_REQUIRED",
        "allowed": allowed,
        "reason": "inside temporary internal envelope" if allowed else "blocked or experiment disabled",
    }
    _event(root, "EXPERIMENT_AUTHORITY_EVALUATED", **result)
    return result

