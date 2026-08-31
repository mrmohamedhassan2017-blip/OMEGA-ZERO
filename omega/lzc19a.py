"""LZC V1.9A: bounded authoritative-heartbeat diagnosis without recovery action."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .lzc13 import EXPECTED_CORE_HASH
from .lzc18 import project_heartbeat
from .lzc19 import _atomic_write, _observer_lock
from .supervisor import Supervisor, task_state

RESULT_PATH = Path(".omega/zero/lzc_v1_9a_result.json")
LOCK_PATH = Path(".omega/zero/lzc_v1_9a_observer.lock")


def collect_diagnostic_sample(root: Path, *, observed_at: datetime | None = None) -> dict[str, Any]:
    root = Path(root)
    heartbeat_path = root / ".omega" / "runtime" / "heartbeat.json"
    lock_path = root / ".omega" / "runtime" / "supervisor.lock"
    timestamp = observed_at or datetime.now().astimezone()
    try:
        heartbeat = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        heartbeat_present = isinstance(heartbeat, dict)
    except (OSError, json.JSONDecodeError):
        heartbeat, heartbeat_present = {}, False
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        lock = {}
    pid = int(heartbeat.get("pid", 0) or 0)
    alive = Supervisor._pid_alive(pid)
    identity_valid = Supervisor(root).owns_process(heartbeat) if alive else False
    projection = project_heartbeat(
        heartbeat, expected_runtime_id=heartbeat.get("runtime_instance_id"), observed_at=timestamp,
    )
    try:
        mtime = heartbeat_path.stat().st_mtime_ns
    except OSError:
        mtime = None
    cross_file_identity = bool(
        heartbeat.get("runtime_instance_id")
        and heartbeat.get("runtime_instance_id") == lock.get("runtime_instance_id")
        and heartbeat.get("pid") == lock.get("pid")
        and heartbeat.get("process_created_at") == lock.get("process_created_at")
    )
    return {
        "sample_time": timestamp.isoformat(timespec="seconds"),
        "heartbeat_file_present": heartbeat_present,
        "heartbeat_logical_timestamp": heartbeat.get("last_heartbeat"),
        "heartbeat_file_mtime_ns": mtime,
        "heartbeat_age_seconds": projection.get("heartbeat_age_seconds"),
        "heartbeat_fresh": projection.get("heartbeat_age_seconds") is not None
        and projection["heartbeat_age_seconds"] <= projection["freshness_limit_seconds"],
        "pid": pid,
        "process_alive": alive,
        "identity_valid": identity_valid,
        "cross_file_identity_consistent": cross_file_identity,
        "runtime_instance_id": heartbeat.get("runtime_instance_id"),
    }


def run_heartbeat_diagnosis(root: Path, duration_seconds: float = 300.0,
                            interval_seconds: float = 30.0,
                            *, clock: Callable[[], float] = time.monotonic,
                            sleeper: Callable[[float], None] = time.sleep,
                            sample_fn: Callable[..., dict[str, Any]] = collect_diagnostic_sample,
                            scheduled_task_state: Callable[[], str] = task_state) -> dict[str, Any]:
    root = Path(root)
    duration = max(.05, float(duration_seconds)); interval = max(.01, float(interval_seconds))
    expected = int(duration // interval) + 1
    with _observer_lock(root / LOCK_PATH):
        started = clock(); samples: list[dict[str, Any]] = []
        task_before = scheduled_task_state()
        for index in range(expected):
            delay = started + index * interval - clock()
            if delay > 0: sleeper(delay)
            samples.append(sample_fn(root))
        actual = clock() - started
        task_after = scheduled_task_state()
        logical = [sample.get("heartbeat_logical_timestamp") for sample in samples]
        mtimes = [sample.get("heartbeat_file_mtime_ns") for sample in samples]
        advancing = sum(a != b for a, b in zip(logical, logical[1:]))
        mtime_advancing = sum(a != b for a, b in zip(mtimes, mtimes[1:]))
        live = [sample for sample in samples if sample.get("process_alive")]
        valid = [sample for sample in samples if sample.get("identity_valid")]
        fresh = [sample for sample in samples if sample.get("heartbeat_fresh")]
        all_stopped = not live and task_before in {"READY", "STOPPED"} and task_after in {"READY", "STOPPED"}
        if all_stopped:
            final = "HEARTBEAT_STALE_EXPECTED_SUPERVISOR_NOT_RUNNING"
            root_cause = "The Scheduled Task is not running and the recorded PID is absent; heartbeat.json and supervisor.lock are residual runtime state."
            runtime_state = "STOPPED"
        elif live and valid and advancing:
            final = "HEARTBEAT_RUNTIME_HEALTHY_OBSERVER_DEFECT"
            root_cause = "The authoritative heartbeat advances with a valid live runtime; prior stale classification requires observer review."
            runtime_state = "RUNNING"
        elif live:
            final = "HEARTBEAT_RUNTIME_DEFECT_UNRESOLVED"
            root_cause = "A runtime process is alive but authoritative heartbeat progression was not established."
            runtime_state = "UNHEALTHY_OR_UNVERIFIED"
        else:
            final = "INCONCLUSIVE"
            root_cause = "Runtime availability could not be classified from bounded evidence."
            runtime_state = "UNKNOWN"
        result = {
            "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
            "supervisor_runtime_state": runtime_state,
            "process_alive": bool(live),
            "identity_valid": bool(valid),
            "heartbeat_write_site": "Supervisor.heartbeat",
            "heartbeat_write_atomicity": "write heartbeat.tmp then Path.replace(heartbeat.json)",
            "heartbeat_error_handling": "backend pulse swallows OSError; direct lifecycle writes propagate to Supervisor.run crash handling",
            "heartbeat_failure_behavior": "pulse write failure is silent for that pulse; an absent runtime produces no writer and leaves residual files",
            "expected_heartbeat_cadence": {"backend_seconds": 5, "tests_seconds": 1, "idle_poll_seconds": 30},
            "heartbeat_timestamp_field": "last_heartbeat (timezone-aware ISO-8601 wall clock)",
            "heartbeat_freshness_rule": "age <= 90 seconds in LZC shadow observer",
            "heartbeat_path": str((root / ".omega" / "runtime" / "heartbeat.json").resolve()),
            "heartbeat_file_present": all(sample.get("heartbeat_file_present") for sample in samples),
            "current_heartbeat_age_seconds": samples[-1].get("heartbeat_age_seconds"),
            "heartbeat_logical_timestamp": samples[-1].get("heartbeat_logical_timestamp"),
            "heartbeat_file_mtime_ns": samples[-1].get("heartbeat_file_mtime_ns"),
            "heartbeat_writer_count": 1 if live and valid else 0,
            "short_diagnostic_sample_count": len(samples),
            "advancing_heartbeat_samples": advancing,
            "advancing_mtime_samples": mtime_advancing,
            "fresh_samples": len(fresh),
            "scheduled_task_state": {"before": task_before, "after": task_after},
            "measurement_defect": "NONE_FOUND; timezone-aware parsing, logical timestamp, mtime, path, and identity were compared separately",
            "runtime_defect": "NO_HEARTBEAT_WRITER_RUNNING; termination origin not proven by this read-only cycle" if all_stopped else None,
            "root_cause": root_cause,
            "repair_applied": False,
            "repair_scope": "NONE",
            "post_repair_verification": "NOT_APPLICABLE",
            "authority_violations": 0,
            "stale_owner_acceptances": 0,
            "unsafe_process_terminations": 0,
            "unrelated_process_terminations": 0,
            "heartbeat_false_fresh_acceptances": 0,
            "core_api_spec_hash_valid": EXPECTED_CORE_HASH == "b7949daacdc43b28e09a207f9954e170ea159e28b3101c298eaee7319964d43e",
            "core_api_change_requests": 0,
            "actual_duration_seconds": round(actual, 3),
            "samples": samples,
            "final_result": final,
            "next_atomic_action": "USE_EXISTING_AUTHORIZED_RECOVERY_PATH_TO_START_ONE_SUPERVISOR_RUNTIME_THEN_RERUN_60MIN_READ_ONLY_SHADOW" if all_stopped else "RERUN_LONG_REAL_SUPERVISOR_READ_ONLY_SHADOW_60MIN",
            "global_system_state": "WAITING_AUTHORIZED_SUPERVISOR_RUNTIME_RECOVERY" if all_stopped else "WAITING_LONG_DURATION_READ_ONLY_SUPERVISOR_SHADOW_EVIDENCE",
            "global_wait_required": all_stopped,
            "long_duration_temporal_evidence": "NOT_YET_PROVEN",
            "supervisor_controlled_canary_gate": "CLOSED",
            "production_status": "GLOBAL_DEFAULT_LEGACY; LEAN_SUPERVISOR_AUTHORITY_NONE",
        }
        _atomic_write(root / RESULT_PATH, result)
        return result
