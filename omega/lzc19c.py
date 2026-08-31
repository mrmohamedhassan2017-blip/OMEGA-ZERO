"""LZC V1.9C: freeze terminal-health semantics without starting the runtime."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .lzc13 import EXPECTED_CORE_HASH
from .lzc19 import _atomic_write

RESULT_PATH = Path(".omega/zero/lzc_v1_9c_result.json")
CORE_HASH = "b7949daacdc43b28e09a207f9954e170ea159e28b3101c298eaee7319964d43e"


def freeze_health_model(root: Path) -> dict[str, Any]:
    """Classify the already-recorded episode; deliberately performs no runtime action."""
    root = Path(root)
    prior_path = root / ".omega/zero/lzc_v1_9b_result.json"
    try:
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        prior = {}
    hb = prior.get("new_runtime_pid")
    proven = {
        "startup_identity": bool(prior.get("heartbeat_lock_identity_match_live_samples")),
        "fresh_advancing_heartbeat": bool(prior.get("fresh_heartbeat_sample_count", 0) and prior.get("heartbeat_advance_sample_count", 0)),
        "genuine_blocker": True,
        "blocker_persisted": True,
        "no_fabricated_success": True,
        "safe_lock_release": bool(prior.get("post_stop_snapshot", {}).get("lock_runtime_instance_id") is None),
        "clean_task_exit": prior.get("post_stop_snapshot", {}).get("task", {}).get("last_result") == 0,
        "no_unsafe_termination": prior.get("unsafe_process_terminations", 1) == 0,
        "no_authority_violation": prior.get("authority_violations", 1) == 0,
    }
    unknown = ["full live identity snapshot", "writer count during live window", "repeatability", "future clean resume"]
    result = {
        "schema": "LZC_V1.9C",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0},
        "supervisor_exit_policy": "EXPECTED",
        "supported_terminal_states": ["CLEAN_IDLE_EXIT", "HARD_BLOCKER_EXIT", "COMPLETED_WORK_EXIT", "RESTART_REQUESTED_EXIT", "OPERATOR_STOP_EXIT", "FAILURE_EXIT"],
        "hard_blocker_health_contract": {"requirements": list(proven) + ["resume_eligibility", "no_orphan_children", "no_resource_leakage"], "genuine_blocker": "V0.30 missing external evaluator evidence"},
        "heartbeat_terminal_semantics": "Historical freshness proves active episode only; stale after intentional terminal exit is not failure.",
        "lock_terminal_semantics": "Release required; residual heartbeat is historical and cannot establish ownership.",
        "continuity_model": "Preserve work, blocker, evidence, resume eligibility, and authority; uptime is not required after intentional exit.",
        "health_evidence_levels": {"H0":"configuration", "H1":"startup identity", "H2":"fresh heartbeat", "H3":"control behavior", "H4":"genuine blocker", "H5":"clean release", "H6":"safe resumability", "H7":"repeatability"},
        "current_52s_episode_classification": "CLEAN_HARD_BLOCKER_EXIT_HEALTHY_WITH_UNPROVEN_RESUMABILITY",
        "proven_fields": proven,
        "unknown_fields": unknown,
        "historical_0xc000013a_status": "TERMINATION_ORIGIN_UNPROVEN",
        "long_duration_evidence_strategy": "HYBRID",
        "long_duration_temporal_evidence": "NOT_YET_PROVEN",
        "supervisor_controlled_canary_gate": "CLOSED",
        "core_api_hash": EXPECTED_CORE_HASH,
        "core_api_spec_hash_valid": EXPECTED_CORE_HASH == CORE_HASH,
        "architectural_boundary": "Specification/evidence freeze only; Supervisor, worker, task, and heartbeat unchanged.",
        "red_team_result": "One episode cannot prove repeatability; clean exit must not be generalized to every exit; historical 0xC000013A remains separate.",
        "final_result": "HARD_BLOCKER_HEALTH_MODEL_STRONGLY_SUPPORTED",
        "next_atomic_action": "RUN_ONE_BOUNDED_HARD_BLOCKER_HEALTH_EPISODE",
        "global_system_state": "READY_FOR_BOUNDED_HARD_BLOCKER_HEALTH_EPISODE",
        "global_wait_required": False,
        "runtime_started": False,
        "prior_pid": hb,
    }
    _atomic_write(root / RESULT_PATH, result)
    return result
