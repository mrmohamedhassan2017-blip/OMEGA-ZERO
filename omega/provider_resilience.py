"""Quota-aware provider registry and restart-safe task scheduling primitives."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_STATES = {"AVAILABLE", "DEGRADED", "RATE_LIMITED", "QUOTA_EXHAUSTED", "WAITING_RESOURCE", "AUTH_FAILED", "BACKEND_FAILED", "UNKNOWN"}
TASK_CLASSES = {"LOCAL_DETERMINISTIC", "LOCAL_TEST", "LOCAL_GIT", "LOCAL_STATE_UPDATE", "AI_REASONING_REQUIRED", "AI_CODE_EDIT_REQUIRED", "EXTERNAL_ACTION", "HUMAN_AUTHORITY_REQUIRED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def backend_registry(*, codex_state: str = "UNKNOWN", next_retry_at: str | None = None,
                     quota_remaining: Any = "UNKNOWN", claude_state: str | None = None,
                     claude_next_retry_at: str | None = None) -> dict[str, Any]:
    if codex_state not in BACKEND_STATES:
        raise ValueError("invalid backend state")
    if claude_state is not None and claude_state not in BACKEND_STATES:
        raise ValueError("invalid Claude backend state")
    backends = [
        {"backend_id": "CODEX_BACKEND", "backend_type": "AI_CODE_EDIT",
         "capabilities": ["reasoning", "code_edit"], "status": codex_state,
         "authorization": "configured provider account", "quota_state": codex_state,
         "quota_remaining": quota_remaining, "next_retry_at": next_retry_at,
         "cost_class": "provider-dependent", "latency_class": "interactive",
         "sandbox_limitations": ["cannot be assumed to execute host Python/tests"],
         "supports_code_edit": True, "supports_shell": False, "supports_tests": False,
         "supports_network": False, "last_success": None, "last_failure": None,
         "failure_class": None, "health_confidence": "UNKNOWN"},
        {"backend_id": "HOST_LOCAL_EXECUTOR", "backend_type": "DETERMINISTIC_HOST",
         "capabilities": ["tests", "git", "state", "hashing", "monitoring"], "status": "AVAILABLE",
         "authorization": "local repository authority", "quota_state": "NOT_APPLICABLE",
         "quota_remaining": "UNKNOWN", "next_retry_at": None, "cost_class": "local",
         "latency_class": "bounded", "sandbox_limitations": [], "supports_code_edit": False,
         "supports_shell": True, "supports_tests": True, "supports_network": True,
          "last_success": _now(), "last_failure": None, "failure_class": None,
          "health_confidence": "VERIFIED"},
    ]
    if claude_state is not None:
        backends.append({
            "backend_id": "CLAUDE_CODE_BACKEND", "backend_type": "AI_CODE_EDIT",
            "capabilities": ["reasoning", "code_edit"], "status": claude_state,
            "authorization": "configured provider account plus bounded TaskEnvelope",
            "quota_state": claude_state, "quota_remaining": "UNKNOWN",
            "next_retry_at": claude_next_retry_at, "cost_class": "provider-dependent",
            "latency_class": "interactive", "sandbox_limitations": [
                "provider API required", "Host Verification required", "external/web/shell tools denied",
            ], "supports_code_edit": True, "supports_shell": False, "supports_tests": False,
            "supports_network": False, "last_success": None, "last_failure": None,
            "failure_class": None, "health_confidence": "MEASURED_ONLY",
        })
    return {"format": "omega.execution-backend-registry", "version": 1, "backends": backends}


def classify_task(action: str, *, requires_reasoning: bool = False, changes_code: bool = False,
                  external: bool = False, human_authority: bool = False) -> str:
    if human_authority: return "HUMAN_AUTHORITY_REQUIRED"
    if external: return "EXTERNAL_ACTION"
    if requires_reasoning and changes_code: return "AI_CODE_EDIT_REQUIRED"
    if requires_reasoning: return "AI_REASONING_REQUIRED"
    low = action.lower()
    if any(x in low for x in ("test", "benchmark", "release", "stability")): return "LOCAL_TEST"
    if any(x in low for x in ("git", "commit", "branch", "diff")): return "LOCAL_GIT"
    if any(x in low for x in ("read state", "heartbeat", "hash", "inspect", "verify")): return "LOCAL_STATE_UPDATE"
    return "LOCAL_DETERMINISTIC"


def checkpoint_task(root: Path, task: dict[str, Any], *, reason: str, backend_used: str,
                    next_retry_at: str | None = None) -> dict[str, Any]:
    required = {"task_id", "branch", "frozen_inputs", "repository_baseline", "files_modified",
                "expected_outputs", "tests_completed", "remaining_work", "evidence_hashes"}
    missing = sorted(required - set(task))
    if missing: raise ValueError("checkpoint missing: " + ",".join(missing))
    checkpoint = {**task, "backend_used": backend_used, "interruption_reason": reason,
                  "next_retry_at": next_retry_at, "checkpointed_at": _now(), "status": "WAITING_RESOURCE"}
    path = root / ".omega" / "runtime" / "provider_checkpoint.json"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False), encoding="utf-8")
    return checkpoint


def schedule_quota_wait(root: Path, task: dict[str, Any], retry_at: str) -> dict[str, Any]:
    if not retry_at: raise ValueError("exact provider retry timestamp required")
    checkpoint = checkpoint_task(root, task, reason="QUOTA_EXHAUSTED", backend_used="CODEX_BACKEND", next_retry_at=retry_at)
    wake = {"state": "WAITING_RESOURCE", "wake_condition": "CODEX_BACKEND_AVAILABLE_AT", "next_retry_at": retry_at,
            "probe_policy": "exactly one bounded availability probe at/after wake", "retry_storm": False}
    path = root / ".omega" / "runtime" / "provider_wake.json"; path.write_text(json.dumps(wake, indent=2), encoding="utf-8")
    return {"checkpoint": checkpoint, "wake": wake}


def run_preb_simulation(root: Path) -> dict[str, Any]:
    task = {"task_id": "preb-integration-task", "branch": "zero-counterparty-work-order-001",
            "frozen_inputs": ["NEXT_TASK.md", "WO-ZERO-001"], "repository_baseline": "verified",
            "files_modified": [], "expected_outputs": ["provider resilience patch"], "tests_completed": [],
            "remaining_work": ["resume task after provider recovery"], "evidence_hashes": []}
    retry_at = "2026-08-28T01:04:00+03:00"
    waiting = schedule_quota_wait(root, task, retry_at)
    waiting["host_continuation"] = {"action": "run deterministic verification", "backend": "HOST_LOCAL_EXECUTOR", "completed": True}
    waiting["recovery_probe"] = {"status": "AVAILABLE", "probes": 1, "resumed_task": task["task_id"], "duplicate_work": False}
    waiting["registry"] = backend_registry(codex_state="AVAILABLE", next_retry_at=retry_at)
    waiting["task_classification"] = {"tests": classify_task("run tests"), "hashes": classify_task("verify hashes"),
                                       "state": classify_task("read state"), "coding": classify_task("repair code", requires_reasoning=True, changes_code=True)}
    path = root / ".omega" / "runtime" / "provider_resilience_simulation.json"; path.write_text(json.dumps(waiting, indent=2), encoding="utf-8")
    return waiting
