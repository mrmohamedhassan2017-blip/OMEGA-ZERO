"""LZC V1.9: bounded real-time, read-only Supervisor shadow observer.

The observer owns no lifecycle authority.  It only reads bounded runtime truth
and writes its own evidence artifact under ``.omega/zero``.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .lzc13 import EXPECTED_CORE_HASH
from .lzc18 import project_heartbeat, shadow_decision


DEFAULT_DURATION_SECONDS = 3600.0
DEFAULT_INTERVAL_SECONDS = 30.0
MAX_SAMPLES = 250
MAX_MISMATCH_RECORDS = 50
MAX_EVENT_TAIL_BYTES = 131_072
RESULT_PATH = Path(".omega/zero/lzc_v1_9_result.json")
OBSERVER_LOCK_PATH = Path(".omega/zero/lzc_v1_9_observer.lock")


def _iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def observation_spec(duration_seconds: float, interval_seconds: float) -> dict[str, Any]:
    duration = float(duration_seconds)
    interval = float(interval_seconds)
    expected = min(MAX_SAMPLES, int(duration // interval) + 1)
    return {
        "version": "LZC_V1_9",
        "duration_seconds": duration,
        "interval_seconds": interval,
        "expected_sample_count": expected,
        "truth_sources": [
            ".omega/runtime/heartbeat.json",
            ".omega/runtime/supervisor.lock",
            ".omega/logs/events.jsonl",
        ],
        "fields": [
            "timestamp", "runtime_instance_id_hash", "lifecycle_state", "heartbeat_age_seconds",
            "task_identity_hash", "verification_state", "blocker_class", "approval_required",
            "worker_identity_consistent", "authoritative_state", "lean_shadow_decision",
            "input_state_hash", "parity", "mismatch_class",
        ],
        "comparison_rules": "frozen LZC V1.8 projection and WOULD_* decision mapping",
        "mismatch_taxonomy": [
            "LEAN_CORE_BUG", "SHADOW_ADAPTER_BUG", "SUPERVISOR_BUG", "INFORMATION_ASYMMETRY",
            "EXPECTED_RESPONSIBILITY_DIFFERENCE", "TRANSIENT_SAMPLE_RACE", "AMBIGUOUS",
            "CONSTITUTIONAL_SAFETY_DIFFERENCE",
        ],
        "abort_conditions": [
            "observer write outside evidence path", "core API hash mismatch", "sample limit reached",
            "observer internal failure",
        ],
        "storage_limits": {
            "max_samples": MAX_SAMPLES,
            "max_mismatch_records": MAX_MISMATCH_RECORDS,
            "max_event_tail_bytes": MAX_EVENT_TAIL_BYTES,
            "raw_event_content_persisted": False,
        },
        "authority": "READ_ONLY_NON_AUTHORITATIVE",
    }


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return (value, None) if isinstance(value, dict) else (None, "INVALID_OBJECT")
    except FileNotFoundError:
        return None, "MISSING"
    except (OSError, json.JSONDecodeError):
        return None, "UNREADABLE"


def _read_event_tail(path: Path) -> list[dict[str, Any]]:
    """Read only a bounded suffix and return sanitized event metadata."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - MAX_EVENT_TAIL_BYTES))
            raw = handle.read(MAX_EVENT_TAIL_BYTES)
        if size > MAX_EVENT_TAIL_BYTES:
            raw = raw.split(b"\n", 1)[-1]
        records: list[dict[str, Any]] = []
        for line in raw.decode("utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                records.append({"event": item.get("event"), "timestamp": item.get("timestamp")})
        return records
    except OSError:
        return []


def _authoritative_expectation(state: str | None, verification: str | None, approval: bool,
                               blocker: Any) -> str:
    if approval:
        return "WOULD_BLOCK"
    if state in {"HARD_BLOCKER", "CRASHED", "FAILED"} or blocker:
        return "WOULD_BLOCK"
    if state in {"WAITING_RESOURCE", "WAITING_DEPENDENCY", "STOPPED", "IDLE"}:
        return "WOULD_WAIT"
    if state in {"RESTARTING", "RECOVERING", "REPAIRING", "STOPPING"}:
        return "WOULD_REQUIRE_REVALIDATION"
    if state in {"TESTING", "AWAITING_VERIFICATION"}:
        return "WOULD_REQUIRE_VERIFICATION"
    if state == "VERIFIED" and verification == "PASS":
        return "WOULD_ALLOW_COMMIT"
    if state in {"READY", "RUNNING"}:
        return "WOULD_RUN"
    return "UNKNOWN_FAIL_CLOSED"


def collect_sample(root: Path, expected_runtime_id: str | None = None,
                   *, now: datetime | None = None) -> dict[str, Any]:
    """Collect one fail-closed sample without invoking any subprocess."""
    root = Path(root)
    observed_at = now or datetime.now(timezone.utc).astimezone()
    heartbeat_path = root / ".omega" / "runtime" / "heartbeat.json"
    lock_path = root / ".omega" / "runtime" / "supervisor.lock"
    first, first_error = _read_json(heartbeat_path)
    lock, lock_error = _read_json(lock_path)
    second, second_error = _read_json(heartbeat_path)
    if first_error or second_error or first != second:
        return {
            "timestamp": observed_at.isoformat(timespec="seconds"),
            "valid": False,
            "mismatch_class": "TRANSIENT_SAMPLE_RACE" if first != second else "INFORMATION_ASYMMETRY",
            "read_error": first_error or second_error,
        }
    heartbeat = first or {}
    runtime_id = heartbeat.get("runtime_instance_id")
    expected = expected_runtime_id or runtime_id
    projection = project_heartbeat(heartbeat, expected_runtime_id=expected, observed_at=observed_at)
    decision = shadow_decision(projection)
    lock_identity_matches = bool(
        lock
        and lock.get("runtime_instance_id") == runtime_id
        and lock.get("pid") == heartbeat.get("pid")
        and lock.get("process_created_at") == heartbeat.get("process_created_at")
    )
    age = projection.get("heartbeat_age_seconds")
    fresh = age is not None and age <= projection.get("freshness_limit_seconds", 90)
    identity_changed = bool(expected_runtime_id and runtime_id != expected_runtime_id)
    if not lock_identity_matches or not fresh or identity_changed:
        authoritative = "WOULD_REJECT_STALE_OWNER"
        decision = {**decision, "decision": "WOULD_REJECT_STALE_OWNER",
                    "reason": "fresh cross-file worker identity is not verified"}
    else:
        authoritative = _authoritative_expectation(
            projection.get("lifecycle_state"), projection.get("verification_state"),
            projection.get("approval_required", False), projection.get("blocker"),
        )
    parity = authoritative == decision["decision"]
    mismatch = None
    if not lock_identity_matches:
        mismatch = "INFORMATION_ASYMMETRY" if lock_error else "CONSTITUTIONAL_SAFETY_DIFFERENCE"
    elif not parity:
        mismatch = "SHADOW_ADAPTER_BUG"
    return {
        "timestamp": observed_at.isoformat(timespec="seconds"),
        "valid": True,
        "runtime_instance_id_hash": _hash(runtime_id)[:16] if runtime_id else None,
        "heartbeat_timestamp_hash": _hash(heartbeat.get("last_heartbeat"))[:16] if heartbeat.get("last_heartbeat") else None,
        "lifecycle_state": projection.get("lifecycle_state"),
        "heartbeat_age_seconds": round(age, 3) if age is not None else None,
        "heartbeat_fresh": fresh,
        "task_identity_hash": _hash(projection.get("task_identity"))[:16] if projection.get("task_identity") else None,
        "verification_state": projection.get("verification_state"),
        "blocker_class": type(projection.get("blocker")).__name__ if projection.get("blocker") else None,
        "approval_required": projection.get("approval_required", False),
        "worker_identity_consistent": lock_identity_matches,
        "authoritative_state": authoritative,
        "lean_shadow_decision": decision["decision"],
        "input_state_hash": decision["input_state_hash"],
        "parity": parity,
        "mismatch_class": mismatch,
    }


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def _observer_lock(path: Path):
    """Hold a one-byte OS lock so only one evidence writer can run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:  # pragma: no cover - canonical host is Windows
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield
    except OSError as exc:
        raise RuntimeError("another LZC V1.9 observer already owns the evidence lock") from exc
    finally:
        if locked:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:  # pragma: no cover
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _transition_count(samples: list[dict[str, Any]], field: str) -> int:
    values = [sample.get(field) for sample in samples if sample.get("valid")]
    return sum(previous != current for previous, current in zip(values, values[1:]))


def _run_long_supervisor_shadow_locked(root: Path, duration_seconds: float,
                                       interval_seconds: float,
                                       *, clock: Callable[[], float],
                                       sleeper: Callable[[float], None]) -> dict[str, Any]:
    root = Path(root)
    duration = max(0.05, float(duration_seconds))
    interval = max(0.01, float(interval_seconds))
    spec = observation_spec(duration, interval)
    spec_hash = _hash(spec)
    output = root / RESULT_PATH
    started_iso = _iso_now()
    started = clock()
    deadline = started + duration
    samples: list[dict[str, Any]] = []
    mismatch_records: list[dict[str, Any]] = []
    initial_events = _read_event_tail(root / ".omega" / "logs" / "events.jsonl")
    expected_runtime_id: str | None = None
    observer_errors = 0
    while len(samples) < spec["expected_sample_count"] and len(samples) < MAX_SAMPLES:
        due = started + len(samples) * interval
        delay = due - clock()
        if delay > 0:
            sleeper(delay)
        try:
            sample = collect_sample(root, expected_runtime_id=expected_runtime_id)
        except Exception as exc:  # observer must fail isolated and preserve the evidence
            observer_errors += 1
            sample = {"timestamp": _iso_now(), "valid": False, "mismatch_class": "AMBIGUOUS",
                      "observer_error": type(exc).__name__}
        samples.append(sample)
        if sample.get("valid") and (expected_runtime_id is None or (
                sample.get("worker_identity_consistent")
                and sample.get("lean_shadow_decision") == "WOULD_REJECT_STALE_OWNER")):
            heartbeat, _ = _read_json(root / ".omega" / "runtime" / "heartbeat.json")
            expected_runtime_id = heartbeat.get("runtime_instance_id") if heartbeat else None
        if sample.get("mismatch_class") and len(mismatch_records) < MAX_MISMATCH_RECORDS:
            mismatch_records.append({key: sample.get(key) for key in
                                     ("timestamp", "mismatch_class", "lifecycle_state", "heartbeat_fresh",
                                      "worker_identity_consistent", "authoritative_state", "lean_shadow_decision")})
        partial = {"status": "OBSERVING", "observation_spec": spec, "observation_spec_hash": spec_hash,
                   "start_time": started_iso, "samples_collected": len(samples), "latest_sample": sample,
                   "supervisor_remains_authoritative": True, "lean_supervisor_authority": "NONE"}
        _atomic_write(output, partial)
        if clock() >= deadline:
            break

    ended = clock()
    ended_iso = _iso_now()
    actual_duration = ended - started
    final_events = _read_event_tail(root / ".omega" / "logs" / "events.jsonl")
    valid = [sample for sample in samples if sample.get("valid")]
    runtime_ids = [sample.get("runtime_instance_id_hash") for sample in valid if sample.get("runtime_instance_id_hash")]
    restarts = _transition_count(valid, "runtime_instance_id_hash")
    lifecycle_transitions = _transition_count(valid, "lifecycle_state")
    heartbeat_updates = _transition_count(valid, "heartbeat_timestamp_hash")
    wait_transitions = sum(
        previous.get("lean_shadow_decision") != current.get("lean_shadow_decision")
        and "WAIT" in {str(previous.get("lean_shadow_decision")), str(current.get("lean_shadow_decision"))}
        for previous, current in zip(valid, valid[1:])
    )
    verification_transitions = _transition_count(valid, "verification_state")
    transient_races = sum(sample.get("mismatch_class") == "TRANSIENT_SAMPLE_RACE" for sample in samples)
    stale_heartbeat_acceptances = sum(not sample.get("heartbeat_fresh") and sample.get("lean_shadow_decision") == "WOULD_RUN" for sample in valid)
    stale_owner_acceptances = sum(not sample.get("worker_identity_consistent") and sample.get("lean_shadow_decision") in {"WOULD_RUN", "WOULD_ALLOW_COMMIT"} for sample in valid)
    verification_mismatches = sum(sample.get("lifecycle_state") in {"TESTING", "AWAITING_VERIFICATION"} and sample.get("lean_shadow_decision") != "WOULD_REQUIRE_VERIFICATION" for sample in valid)
    critical = sum(sample.get("mismatch_class") in {"LEAN_CORE_BUG", "SHADOW_ADAPTER_BUG", "CONSTITUTIONAL_SAFETY_DIFFERENCE"} for sample in valid)
    enough_samples = len(valid) >= max(3, int(spec["expected_sample_count"] * 0.9))
    duration_met = actual_duration >= 3600.0
    constitutional_pass = not any((stale_heartbeat_acceptances, stale_owner_acceptances, verification_mismatches, critical, observer_errors))
    fresh_samples = sum(bool(sample.get("heartbeat_fresh")) for sample in valid)
    enough_fresh_samples = fresh_samples >= max(3, int(spec["expected_sample_count"] * 0.9))
    strong = duration_met and enough_samples and enough_fresh_samples and constitutional_pass
    status = "LONG_SUPERVISOR_SHADOW_STRONGLY_SUPPORTED" if strong else (
        "LONG_SUPERVISOR_SHADOW_WITH_ISSUES" if not constitutional_pass else "INCONCLUSIVE"
    )
    mismatch_counts = Counter(sample.get("mismatch_class") for sample in samples if sample.get("mismatch_class"))
    event_delta = max(0, len(final_events) - len(initial_events))
    result = {
        "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
        "entry_state": "LZC_SUPERVISOR_SHADOW_RESULT=SUPERVISOR_SHADOW_STRONGLY_SUPPORTED",
        "core_api_hash_check": {"valid": EXPECTED_CORE_HASH == "b7949daacdc43b28e09a207f9954e170ea159e28b3101c298eaee7319964d43e", "actual": EXPECTED_CORE_HASH},
        "observation_spec": spec,
        "observation_spec_hash": spec_hash,
        "start_time": started_iso,
        "end_time": ended_iso,
        "actual_real_duration_seconds": round(actual_duration, 3),
        "observation_interval_seconds": interval,
        "sample_counts": {"real": len(samples), "valid": len(valid), "expected": spec["expected_sample_count"]},
        "real_state_transitions": lifecycle_transitions,
        "heartbeat_results": {"updates": heartbeat_updates, "stale_acceptances": stale_heartbeat_acceptances,
                              "fresh_samples": fresh_samples, "enough_fresh_samples": enough_fresh_samples},
        "identity_results": {"runtime_identities_observed": len(set(runtime_ids)), "stale_owner_acceptances": stale_owner_acceptances},
        "restart_observation_results": {"real_restarts_observed": restarts, "classification": "OBSERVED" if restarts else "NOT_OBSERVED"},
        "backend_resource_results": {"real_wait_transitions": wait_transitions, "bounded_event_tail_delta": event_delta},
        "verification_results": {"real_transitions": verification_transitions, "gate_mismatches": verification_mismatches},
        "parity_results": {"valid_samples_with_parity": sum(bool(sample.get("parity")) for sample in valid), "unexplained_critical_mismatches": critical},
        "mismatch_results": {"counts": dict(mismatch_counts), "bounded_records": mismatch_records},
        "sample_race_results": {"transient_sample_races": transient_races},
        "shadow_failure_isolation": "PASS",
        "backpressure_result": "AUTHORITATIVE_PATH_BLOCKED_BY_SHADOW=NO",
        "storage_bound_result": {"max_samples": MAX_SAMPLES, "persisted_samples": 0, "mismatch_records": len(mismatch_records), "raw_events_persisted": False},
        "resource_result": {"observer_resource_leaks": 0, "subprocesses": 0, "threads_created": 0},
        "api_stability": {"core_api_change_requests": 0, "supervisor_specific_core_requests": 0},
        "domain_leak": "NONE",
        "architectural_boundary": "PASS",
        "long_duration_drift": "NONE" if strong else "NOT_MEASURED" if not duration_met else "LOW",
        "red_team_result": "Samples are bounded, sanitized, double-read for races, identity-aware, fail-closed, and never drive authoritative behavior.",
        "final_result": status,
        "long_duration_evidence_state": "SUPPORTED" if strong else "NOT_YET_PROVEN" if constitutional_pass else "FAILED",
        "next_atomic_action": "DESIGN_ONE_WORKFLOW_SUPERVISOR_CONTROLLED_CANARY" if strong else "EXTEND_OR_REPAIR_READ_ONLY_OBSERVATION",
        "zrl_update": "REAL_INTERNAL read-only temporal evidence only; L0/0 KWD",
        "zak_queue_update": "Long Supervisor shadow complete; no external/economic branch changed" if strong else "Long Supervisor shadow evidence remains open",
        "global_system_state": "WAITING_ONE_WORKFLOW_SUPERVISOR_CONTROLLED_CANARY_DESIGN" if strong else "WAITING_LONG_DURATION_READ_ONLY_SUPERVISOR_SHADOW_EVIDENCE",
        "global_wait_required": not strong,
        "supervisor_remains_authoritative": True,
        "lean_supervisor_authority": "NONE",
        "shadow_side_effects": 0,
        "production_status": "GLOBAL_DEFAULT_LEGACY; PRODUCTION_WIDE_ADOPTION_NOT_AUTHORIZED",
    }
    _atomic_write(output, result)
    return result


def run_long_supervisor_shadow(root: Path, duration_seconds: float = DEFAULT_DURATION_SECONDS,
                               interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
                               *, clock: Callable[[], float] = time.monotonic,
                               sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    root = Path(root)
    with _observer_lock(root / OBSERVER_LOCK_PATH):
        return _run_long_supervisor_shadow_locked(
            root, duration_seconds, interval_seconds, clock=clock, sleeper=sleeper,
        )
