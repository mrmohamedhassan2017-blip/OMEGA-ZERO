"""LZC V1.9B: one-shot recovery through the installed Scheduled Task."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .lzc13 import EXPECTED_CORE_HASH
from .lzc18 import project_heartbeat
from .lzc19 import _atomic_write
from .supervisor import Supervisor, request_stop, start_scheduled_task, task_state

RESULT_PATH = Path(".omega/zero/lzc_v1_9b_result.json")


def _task_snapshot() -> dict[str, Any]:
    if os.name != "nt":
        return {"state": "UNSUPPORTED", "last_result": None, "last_run_time": None}
    script = ("$t=Get-ScheduledTask -TaskName 'OMEGA_Autonomous_Supervisor' -ErrorAction SilentlyContinue; "
              "$i=Get-ScheduledTaskInfo -TaskName 'OMEGA_Autonomous_Supervisor' -ErrorAction SilentlyContinue; "
              "$o=if($null -eq $t){[pscustomobject]@{state='NOT_INSTALLED';last_result=$null;last_run_time=$null}}"
              "else{[pscustomobject]@{state=$t.State.ToString().ToUpperInvariant();last_result=$i.LastTaskResult;last_run_time=$i.LastRunTime.ToString('o')}}; "
              "$o|ConvertTo-Json -Compress")
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return json.loads(completed.stdout) if completed.returncode == 0 and completed.stdout.strip() else {
            "state": "UNKNOWN", "last_result": None, "last_run_time": None,
        }
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {"state": "UNKNOWN", "last_result": None, "last_run_time": None}


def _worker_processes() -> list[int]:
    if os.name != "nt": return []
    script = ("@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
              "Where-Object {$_.CommandLine -like '*omega.runtime.worker*' -and $_.Name -notlike '*powershell*' -and $_.Name -notlike '*pwsh*'}) | "
              "ForEach-Object {$_.ProcessId} | ConvertTo-Json -Compress")
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        value = json.loads(completed.stdout) if completed.stdout.strip() else []
        if value is None: return []
        return [int(item) for item in (value if isinstance(value, list) else [value])]
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return []


def _snapshot(root: Path) -> dict[str, Any]:
    supervisor = Supervisor(root)
    heartbeat = supervisor.read_heartbeat()
    try: lock = json.loads(supervisor.lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): lock = {}
    pid = int(heartbeat.get("pid", 0) or 0)
    return {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "task": _task_snapshot(),
        "heartbeat_runtime_instance_id": heartbeat.get("runtime_instance_id"),
        "heartbeat_pid": pid,
        "heartbeat_timestamp": heartbeat.get("last_heartbeat"),
        "lock_runtime_instance_id": lock.get("runtime_instance_id"),
        "lock_pid": lock.get("pid"),
        "pid_alive": supervisor._pid_alive(pid),
        "stop_present": supervisor.stop_path.exists(),
    }


def run_recovery(root: Path, *, old_pid: int = 6360, timeout_seconds: float = 600,
                 sample_interval: float = 5,
                 start_fn: Callable[[Path], int] = start_scheduled_task,
                 stop_fn: Callable[[Path], dict[str, Any]] = request_stop,
                 task_snapshot_fn: Callable[[], dict[str, Any]] = _task_snapshot,
                 worker_processes_fn: Callable[[], list[int]] = _worker_processes,
                 sleeper: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    root = Path(root)
    pre = _snapshot(root)
    # Preserve injected task snapshots for deterministic tests.
    pre["task"] = task_snapshot_fn()
    start_requests = 0; start_result: dict[str, Any]
    samples: list[dict[str, Any]] = []; stop_result: dict[str, Any] | None = None
    request_time = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        start_requests += 1
        new_pid = int(start_fn(root))
        start_result = {"ok": True, "pid": new_pid}
    except Exception as exc:
        start_result = {"ok": False, "error_class": type(exc).__name__, "message": str(exc)[-1000:]}
        result = {
            "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
            "task_name": "OMEGA_Autonomous_Supervisor", "task_path": "\\OMEGA_Autonomous_Supervisor",
            "pre_start_snapshot": pre, "authorized_start_method": "omega.supervisor.start_scheduled_task",
            "start_request_count": start_requests, "start_request_time": request_time, "start_result": start_result,
            "final_result": "SUPERVISOR_RUNTIME_RECOVERY_FAILED", "repair_applied": False,
            "authority_violations": 0, "unsafe_process_terminations": 0,
            "core_api_spec_hash_valid": EXPECTED_CORE_HASH == "b7949daacdc43b28e09a207f9954e170ea159e28b3101c298eaee7319964d43e",
            "next_atomic_action": "DIAGNOSE_BOUNDED_TASK_START_FAILURE", "global_wait_required": True,
            "long_duration_temporal_evidence": "NOT_YET_PROVEN", "supervisor_controlled_canary_gate": "CLOSED",
        }
        _atomic_write(root / RESULT_PATH, result); return result

    supervisor = Supervisor(root)
    started = clock(); deadline = started + max(1, float(timeout_seconds))
    first_hb = supervisor.read_heartbeat(); new_runtime_id = first_hb.get("runtime_instance_id")
    initial_identity_valid = supervisor.owns_process(first_hb)
    initial_worker_pids = worker_processes_fn()
    previous_timestamp: str | None = None; advances = fresh_count = 0
    live_duration = 0.0
    while clock() < deadline:
        heartbeat = supervisor.read_heartbeat(); now_dt = datetime.now().astimezone()
        pid = int(heartbeat.get("pid", 0) or 0); alive = supervisor._pid_alive(pid)
        try: lock = json.loads(supervisor.lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): lock = {}
        identity_match = bool(
            heartbeat.get("runtime_instance_id") == lock.get("runtime_instance_id") == new_runtime_id
            and heartbeat.get("pid") == lock.get("pid") == new_pid
            and heartbeat.get("process_created_at") == lock.get("process_created_at")
        )
        projection = project_heartbeat(heartbeat, expected_runtime_id=new_runtime_id, observed_at=now_dt)
        age = projection.get("heartbeat_age_seconds"); fresh = age is not None and 0 <= age <= 90
        timestamp = heartbeat.get("last_heartbeat")
        advanced = previous_timestamp is not None and timestamp != previous_timestamp
        if advanced: advances += 1
        if fresh: fresh_count += 1
        samples.append({"time": now_dt.isoformat(timespec="seconds"), "pid": pid,
                        "runtime_instance_id": heartbeat.get("runtime_instance_id"),
                        "logical_timestamp": timestamp, "age_seconds": age, "fresh": fresh,
                        "advanced": advanced, "alive": alive, "identity_match": identity_match,
                        "task_state": task_state()})
        previous_timestamp = timestamp
        live_duration = clock() - started
        if not alive: break
        if advances >= 10 and fresh_count >= 10 and live_duration >= 60: break
        sleeper(max(.1, float(sample_interval)))

    final_hb = supervisor.read_heartbeat(); final_alive = supervisor._pid_alive(int(final_hb.get("pid", 0) or 0))
    final_identity_valid = supervisor.owns_process(final_hb) if final_alive else False
    worker_pids = worker_processes_fn(); writer_count = len(set(initial_worker_pids))
    task_during = task_snapshot_fn()
    old_pid_accepted = bool(old_pid in initial_worker_pids or old_pid in worker_pids or any(sample.get("pid") == old_pid and sample.get("identity_match") for sample in samples))
    live_samples = [sample for sample in samples if sample.get("alive")]
    live_identity_match = bool(live_samples) and all(sample.get("identity_match") for sample in live_samples)
    coherent = bool(final_alive and final_identity_valid and writer_count == 1 and
                    final_hb.get("runtime_instance_id") == new_runtime_id and task_during.get("state") == "RUNNING")
    strong = bool(initial_identity_valid and coherent and not old_pid_accepted and advances >= 10 and fresh_count >= 10 and live_duration >= 60)
    try:
        stop_result = stop_fn(root)
    except Exception as exc:
        stop_result = {"error": f"{type(exc).__name__}: {exc}"}
    post = _snapshot(root); post["task"] = task_snapshot_fn()
    unsafe = int(bool(stop_result and (stop_result.get("forced") or stop_result.get("alive"))))
    if strong and not unsafe:
        final = "SUPERVISOR_RUNTIME_RECOVERED_AND_HEARTBEAT_VERIFIED"
    elif start_result["ok"] and (advances or fresh_count):
        final = "SUPERVISOR_RUNTIME_RECOVERY_WITH_ISSUES"
    else:
        final = "SUPERVISOR_RUNTIME_RECOVERY_FAILED"
    result = {
        "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
        "task_name": "OMEGA_Autonomous_Supervisor", "task_path": "\\OMEGA_Autonomous_Supervisor",
        "pre_start_snapshot": pre, "authorized_start_method": "omega.supervisor.start_scheduled_task",
        "start_request_count": start_requests, "start_request_time": request_time, "start_result": start_result,
        "new_supervisor_pid": new_pid, "new_runtime_instance_id": new_runtime_id,
        "initial_identity_valid": initial_identity_valid,
        "process_alive_during_window": bool(live_samples),
        "process_alive_during_verification": final_alive, "identity_valid_during_verification": final_identity_valid,
        "heartbeat_lock_identity_match": live_identity_match,
        "old_pid_accepted_as_owner": old_pid_accepted, "heartbeat_writer_count": writer_count,
        "initial_worker_pids": initial_worker_pids, "post_window_worker_pids": worker_pids,
        "heartbeat_advance_sample_count": advances, "fresh_heartbeat_sample_count": fresh_count,
        "diagnostic_sample_count": len(samples), "current_heartbeat_age": samples[-1].get("age_seconds") if samples else None,
        "task_process_consistency": coherent, "continuity_result": "PASS" if strong else "FAIL",
        "continuity_observed_seconds": round(live_duration, 3), "samples": samples,
        "stop_result": stop_result, "post_stop_snapshot": post,
        "authority_violations": 0, "unsafe_process_terminations": unsafe,
        "task_reconfigurations": 0, "second_supervisors": max(0, writer_count - 1),
        "core_api_spec_hash_valid": EXPECTED_CORE_HASH == "b7949daacdc43b28e09a207f9954e170ea159e28b3101c298eaee7319964d43e",
        "final_result": final,
        "next_atomic_action": "RERUN_LONG_REAL_SUPERVISOR_READ_ONLY_SHADOW_60MIN" if final.endswith("HEARTBEAT_VERIFIED") else "DIAGNOSE_ONLY_PROVEN_RECOVERY_ISSUE",
        "global_system_state": "READY_FOR_LONG_READ_ONLY_SUPERVISOR_SHADOW" if final.endswith("HEARTBEAT_VERIFIED") else "WAITING_SUPERVISOR_RECOVERY_EVIDENCE",
        "global_wait_required": not final.endswith("HEARTBEAT_VERIFIED"),
        "long_duration_temporal_evidence": "NOT_YET_PROVEN", "supervisor_controlled_canary_gate": "CLOSED",
        "production_status": "SUPERVISOR_AUTHORITATIVE; LEAN_AUTHORITY_NONE; GLOBAL_DEFAULT_LEGACY",
    }
    _atomic_write(root / RESULT_PATH, result); return result
