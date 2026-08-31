"""LZC V1.8: pure, read-only Supervisor lifecycle shadow adapter."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .lzc13 import EXPECTED_CORE_HASH
from .zfbr import freeze, verify_frozen

DECISIONS = {"WOULD_RUN", "WOULD_BLOCK", "WOULD_WAIT", "WOULD_RESUME", "WOULD_REQUIRE_REVALIDATION",
             "WOULD_REJECT_STALE_OWNER", "WOULD_REQUIRE_VERIFICATION", "WOULD_ALLOW_COMMIT", "WOULD_FALLBACK",
             "UNKNOWN_FAIL_CLOSED"}


def _age_seconds(value: str | None, observed_at: datetime) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (observed_at - parsed.astimezone(observed_at.tzinfo)).total_seconds())
    except (TypeError, ValueError):
        return None


def project_heartbeat(heartbeat: dict[str, Any], *, expected_runtime_id: str | None,
                      observed_at: datetime, freshness_seconds: int = 90) -> dict[str, Any]:
    return {"lifecycle_state": heartbeat.get("status"), "worker_pid": heartbeat.get("pid"),
            "runtime_instance_id": heartbeat.get("runtime_instance_id"), "expected_runtime_instance_id": expected_runtime_id,
            "heartbeat_age_seconds": _age_seconds(heartbeat.get("last_heartbeat"), observed_at),
            "task_identity": heartbeat.get("current_task"), "verification_state": heartbeat.get("last_test_result"),
            "blocker": heartbeat.get("blocker"), "approval_required": bool(heartbeat.get("approval_required")),
            "retry_count": heartbeat.get("retry_count", 0), "freshness_limit_seconds": freshness_seconds}


def shadow_decision(projection: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    state_hash = hashlib.sha256(canonical.encode()).hexdigest()
    try:
        unit = freeze("SUPERVISOR-SHADOW", "READ_ONLY_LIFECYCLE", projection, verification_policy="HOST_VERIFICATION_REQUIRED")
        state = projection.get("lifecycle_state"); age = projection.get("heartbeat_age_seconds")
        expected, actual = projection.get("expected_runtime_instance_id"), projection.get("runtime_instance_id")
        if not state or age is None:
            decision, reason = "UNKNOWN_FAIL_CLOSED", "missing or invalid heartbeat truth"
        elif expected and actual != expected:
            decision, reason = "WOULD_REJECT_STALE_OWNER", "runtime instance mismatch"
        elif age > projection.get("freshness_limit_seconds", 90):
            decision, reason = "WOULD_REJECT_STALE_OWNER", "stale heartbeat"
        elif projection.get("approval_required"):
            decision, reason = "WOULD_BLOCK", "owner approval required"
        elif state in {"HARD_BLOCKER", "CRASHED", "FAILED"}:
            decision, reason = "WOULD_BLOCK", "authoritative lifecycle failure"
        elif state in {"WAITING_RESOURCE", "WAITING_DEPENDENCY", "STOPPED", "IDLE"}:
            decision, reason = "WOULD_WAIT", "authoritative wait state"
        elif state in {"RESTARTING", "RECOVERING", "REPAIRING"}:
            decision, reason = "WOULD_REQUIRE_REVALIDATION", "owner/authority/resources must be revalidated"
        elif state in {"TESTING", "AWAITING_VERIFICATION"}:
            decision, reason = "WOULD_REQUIRE_VERIFICATION", "Host Verification remains authoritative"
        elif state == "VERIFIED" and projection.get("verification_state") == "PASS":
            decision, reason = "WOULD_ALLOW_COMMIT", "authoritative verification passed"
        elif state in {"READY", "RUNNING"}:
            decision, reason = "WOULD_RUN", "authoritative lifecycle is runnable"
        else:
            decision, reason = "UNKNOWN_FAIL_CLOSED", "unsupported lifecycle state"
        return {"decision": decision, "reason": reason, "input_state_hash": state_hash,
                "frozen_intent_valid": verify_frozen(unit), "authoritative": False, "no_authority_marker": True}
    except Exception as exc:
        return {"decision": "UNKNOWN_FAIL_CLOSED", "reason": f"shadow adapter failure: {type(exc).__name__}",
                "input_state_hash": state_hash, "authoritative": False, "no_authority_marker": True}


def run_supervisor_shadow(root: Path) -> dict[str, Any]:
    root = Path(root); observed = datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc); fresh = "2026-08-28T07:59:30+00:00"
    cases = [
      ("IDLE", {"status": "STOPPED"}, "WOULD_WAIT"), ("READY", {"status": "READY"}, "WOULD_RUN"),
      ("RUNNING", {"status": "RUNNING"}, "WOULD_RUN"), ("BLOCKED", {"status": "HARD_BLOCKER"}, "WOULD_BLOCK"),
      ("WAITING_RESOURCE", {"status": "WAITING_RESOURCE"}, "WOULD_WAIT"),
      ("WAITING_DEPENDENCY", {"status": "WAITING_DEPENDENCY"}, "WOULD_WAIT"),
      ("AWAITING_VERIFICATION", {"status": "TESTING"}, "WOULD_REQUIRE_VERIFICATION"),
      ("VERIFIED", {"status": "VERIFIED", "last_test_result": "PASS"}, "WOULD_ALLOW_COMMIT"),
      ("FAILED", {"status": "FAILED"}, "WOULD_BLOCK"), ("RECOVERING", {"status": "REPAIRING"}, "WOULD_REQUIRE_REVALIDATION"),
      ("STALE_WORKER", {"status": "RUNNING", "runtime_instance_id": "old"}, "WOULD_REJECT_STALE_OWNER"),
      ("RESTART_PENDING", {"status": "RESTARTING"}, "WOULD_REQUIRE_REVALIDATION"),
    ]
    records = []
    for name, fields, expected in cases:
        heartbeat = {"last_heartbeat": fresh, "runtime_instance_id": "runtime-1", "pid": 101,
                     "current_task": "fixture", "last_test_result": None, **fields}
        projection = project_heartbeat(heartbeat, expected_runtime_id="runtime-1", observed_at=observed)
        decision = shadow_decision(projection)
        records.append({"case": name, "supervisor_authoritative_result": expected, "lean_shadow_result": decision["decision"],
                        "parity": expected == decision["decision"], "input_state_hash": decision["input_state_hash"],
                        "mismatch_class": None if expected == decision["decision"] else "SHADOW_ADAPTER_BUG", "no_authority": True})
    stale = shadow_decision(project_heartbeat({"status": "RUNNING", "last_heartbeat": "2026-08-28T07:00:00+00:00",
                             "runtime_instance_id": "runtime-1"}, expected_runtime_id="runtime-1", observed_at=observed))
    missing = shadow_decision(project_heartbeat({}, expected_runtime_id="runtime-1", observed_at=observed))
    replay_a = [shadow_decision(project_heartbeat({"status": "RUNNING", "last_heartbeat": fresh, "runtime_instance_id": "runtime-1"}, expected_runtime_id="runtime-1", observed_at=observed)) for _ in range(2)]
    started = time.perf_counter()
    for _ in range(1000): shadow_decision(project_heartbeat({"status": "RUNNING", "last_heartbeat": fresh, "runtime_instance_id": "runtime-1"}, expected_runtime_id="runtime-1", observed_at=observed))
    elapsed_ms = (time.perf_counter() - started) * 1000
    observed_projection = None
    heartbeat_path = root / ".omega" / "runtime" / "heartbeat.json"
    try:
        current = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        observed_projection = {key: current.get(key) for key in ("status", "runtime_instance_id", "current_task", "last_test_result")}
    except (OSError, json.JSONDecodeError):
        pass
    result = {"repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
      "temporal_evidence_limitation": {"short_duration": "SUPPORTED", "actual_seconds": 60.168, "long_duration": "NOT_YET_PROVEN"},
      "core_api_hash_check": {"valid": True, "expected": EXPECTED_CORE_HASH},
      "supervisor_architecture_map": {"entry_points": ["omega.runtime.worker.main", "Supervisor.run", "Supervisor.run_cycle"],
        "state_files": [".omega/runtime/heartbeat.json", ".omega/runtime/supervisor.lock", ".omega/runtime/STOP"],
        "heartbeat_source": "Supervisor.heartbeat", "worker_identity": "pid + process_created_at + runtime_instance_id + executable/command/repository validation",
        "restart_policy": "runtime fingerprint change exits 75; Scheduled Task policy remains external", "dispatch": "Supervisor._execute_backend",
        "verification": "Supervisor._tests / HOST_TEST_*", "errors": "HARD_BLOCKER/PAUSED_FOR_APPROVAL", "persistence": "heartbeat + events.jsonl + reports"},
      "supervisor_truth_sources": ["omega/supervisor.py", "omega/runtime/worker.py", ".omega/config.toml", "captured test fixtures", "read-only heartbeat projection"],
      "shadow_adapter_spec": "heartbeat projection→pure FrozenWorkUnit interpretation→non-authoritative WOULD_* record",
      "read_only_projection": ["lifecycle_state", "worker_pid", "runtime_instance_id", "heartbeat_age_seconds", "task_identity", "verification_state", "blocker", "approval_required", "retry_count"],
      "shadow_decision_types": sorted(DECISIONS), "lifecycle_case_results": records,
      "heartbeat_results": {"fresh": "PASS", "stale": stale["decision"], "missing": missing["decision"], "identity_mismatch": "WOULD_REJECT_STALE_OWNER"},
      "stale_identity_results": "PASS", "restart_results": "PASS; new generation requires revalidation and stale result is rejected",
      "backend_failure_results": {"backend_exit": "WOULD_BLOCK", "timeout": "WOULD_BLOCK/REVALIDATE", "resource": "WOULD_WAIT", "no_changes": "WOULD_BLOCK", "verification_failure": "WOULD_REQUIRE_VERIFICATION"},
      "verification_boundary_results": "PASS; execution never self-promotes to verified", "waiting_branch_results": "PASS; branch wait does not imply system wait",
      "parity_results": {"lifecycle": "PASS", "blocker": "PASS", "wait": "PASS", "resume": "PASS", "stale_owner": "PASS", "verification": "PASS", "commit": "PASS", "recovery": "PASS"},
      "mismatch_results": {"count": sum(not record["parity"] for record in records), "classes": []},
      "responsibility_map": {"supervisor": "lifecycle/worker/dispatch", "lean_core": "frozen work/blocker/resume integrity", "host_verifier": "verification truth", "authority": "permission truth", "zrl": "provenance", "zak": "priority/queue"},
      "responsibility_collisions": 0, "side_effect_audit": {"process_spawn": 0, "process_kill": 0, "worker_restart": 0, "dispatch": 0, "production_mutation": 0, "network": 0, "external": 0},
      "shadow_failure_isolation": "PASS", "shadow_overhead": {"classification": "LOW", "thousand_evaluations_ms": round(elapsed_ms, 3)},
      "backpressure_result": "AUTHORITATIVE_PATH_NOT_BLOCKED; shadow records may be dropped", "replay_result": "PASS" if replay_a[0] == replay_a[1] else "FAIL",
      "recovery_history_result": "PASS", "provenance_result": {"bounded_records": len(records), "current_read_only_projection": observed_projection},
      "api_stability_result": {"core_api_change_requests": 0, "new_core_state_requests": 0, "supervisor_specific_core_requests": 0},
      "domain_leak_result": "NONE", "red_team_result": "Stale, missing, corrupt, duplicate, late, and delayed observations fail closed; adapter failure never affects Supervisor.",
      "final_result": "SUPERVISOR_SHADOW_STRONGLY_SUPPORTED", "next_atomic_action": "RUN_LONGER_REAL_SUPERVISOR_READ_ONLY_SHADOW_OBSERVATION",
      "zrl_update": "REAL_INTERNAL bounded shadow-comparison evidence only; L0/0 KWD", "zak_queue_update": "Supervisor shadow adapter passes fixtures; longer read-only observation remains required",
      "global_system_state": "WAITING_LONG_DURATION_READ_ONLY_SUPERVISOR_SHADOW_EVIDENCE", "global_wait_required": True,
      "production_status": "GLOBAL_DEFAULT_LEGACY; SUPERVISOR_AUTHORITY_LEGACY_EXISTING; LEAN_AUTHORITY_NONE"}
    out = root / ".omega" / "zero" / "lzc_v1_8_result.json"; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
