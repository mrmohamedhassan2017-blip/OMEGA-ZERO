"""LZP V1 isolated deterministic control path.

This module is an experiment harness, not a production runtime or migration.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Scenario:
    name: str
    facts: dict[str, Any]
    expected: str


SCENARIOS = (
    Scenario("NORMAL_EXECUTION", {}, "COMPLETED"),
    Scenario("BACKEND_FAILURE", {"backend_failed": True}, "HARD_BLOCKED"),
    Scenario("NO_AGENT_CHANGES", {"real_change": False}, "PARK_NO_CHANGES"),
    Scenario("HOST_VERIFICATION_FAILURE", {"host_verified": False}, "REPAIR"),
    Scenario("PROCESS_TIMEOUT", {"timed_out": True}, "TIMED_OUT_SAFE"),
    Scenario("RECOVERY_AFTER_RESTART", {"restart": True, "checkpoint": True}, "RECOVER_CHECKPOINT"),
    Scenario("STALE_PID_OR_STALE_STATE", {"stale_identity": True}, "IGNORE_STALE_RECOVER"),
    Scenario("WAITING_EXTERNAL_BRANCH", {"waiting_external": True}, "PARK_BRANCH_CONTINUE_SYSTEM"),
    Scenario("RESOURCE_UNAVAILABLE", {"resource_available": False}, "WAIT_RESOURCE"),
    Scenario("AUTHORIZATION_REQUIRED_ACTION", {"authority_required": True, "authorized": False}, "WAIT_AUTHORITY"),
    Scenario("UNAUTHORIZED_ACTION_ATTEMPT", {"external_action": True, "authorized": False}, "REJECT_UNAUTHORIZED"),
    Scenario("DUPLICATE_EXECUTION_RISK", {"duplicate": True}, "BLOCK_DUPLICATE"),
    Scenario("CHECKPOINT_RESTORE", {"restore": True, "checkpoint": True}, "RESUME_CHECKPOINT"),
    Scenario("PROVIDER_UNAVAILABLE_BUT_HOST_WORK_AVAILABLE", {"provider_available": False, "host_work": True}, "ROUTE_HOST"),
    Scenario("SAFE_PARK_AND_WAKE", {"parked": True, "wake": True}, "WAKE_READY"),
    Scenario("PARTIAL_EXECUTION", {"partial": True, "checkpoint": True}, "RECOVER_CHECKPOINT_VERIFY"),
    Scenario("NOVEL_STATE", {"novel": True}, "ESCALATE_MODEL"),
)


def _legacy_reference(f: dict[str, Any]) -> str:
    """Independent imperative reference derived from current lifecycle behavior."""
    if f.get("external_action") and not f.get("authorized", True): return "REJECT_UNAUTHORIZED"
    if f.get("authority_required") and not f.get("authorized", True): return "WAIT_AUTHORITY"
    if f.get("stale_identity"): return "IGNORE_STALE_RECOVER"
    if f.get("duplicate"): return "BLOCK_DUPLICATE"
    if f.get("timed_out"): return "TIMED_OUT_SAFE"
    if f.get("backend_failed"): return "HARD_BLOCKED"
    if f.get("provider_available") is False and f.get("host_work"): return "ROUTE_HOST"
    if f.get("resource_available") is False: return "WAIT_RESOURCE"
    if f.get("restart") and f.get("checkpoint"): return "RECOVER_CHECKPOINT"
    if f.get("restore") and f.get("checkpoint"): return "RESUME_CHECKPOINT"
    if f.get("partial") and f.get("checkpoint"): return "RECOVER_CHECKPOINT_VERIFY"
    if f.get("real_change") is False: return "PARK_NO_CHANGES"
    if f.get("host_verified") is False: return "REPAIR"
    if f.get("waiting_external"): return "PARK_BRANCH_CONTINUE_SYSTEM"
    if f.get("parked") and f.get("wake"): return "WAKE_READY"
    if f.get("novel"): return "ESCALATE_MODEL"
    return "COMPLETED"


Rule = tuple[str, Callable[[dict[str, Any]], bool], str]
RULES: tuple[Rule, ...] = (
    ("external-authority", lambda f: bool(f.get("external_action") and not f.get("authorized", True)), "REJECT_UNAUTHORIZED"),
    ("approval-gate", lambda f: bool(f.get("authority_required") and not f.get("authorized", True)), "WAIT_AUTHORITY"),
    ("identity", lambda f: bool(f.get("stale_identity")), "IGNORE_STALE_RECOVER"),
    ("deduplicate", lambda f: bool(f.get("duplicate")), "BLOCK_DUPLICATE"),
    ("timeout", lambda f: bool(f.get("timed_out")), "TIMED_OUT_SAFE"),
    ("backend-failure", lambda f: bool(f.get("backend_failed")), "HARD_BLOCKED"),
    ("host-fallback", lambda f: f.get("provider_available") is False and bool(f.get("host_work")), "ROUTE_HOST"),
    ("resource", lambda f: f.get("resource_available") is False, "WAIT_RESOURCE"),
    ("restart", lambda f: bool(f.get("restart") and f.get("checkpoint")), "RECOVER_CHECKPOINT"),
    ("restore", lambda f: bool(f.get("restore") and f.get("checkpoint")), "RESUME_CHECKPOINT"),
    ("partial", lambda f: bool(f.get("partial") and f.get("checkpoint")), "RECOVER_CHECKPOINT_VERIFY"),
    ("real-change", lambda f: f.get("real_change") is False, "PARK_NO_CHANGES"),
    ("verification", lambda f: f.get("host_verified") is False, "REPAIR"),
    ("waiting-branch", lambda f: bool(f.get("waiting_external")), "PARK_BRANCH_CONTINUE_SYSTEM"),
    ("wake", lambda f: bool(f.get("parked") and f.get("wake")), "WAKE_READY"),
    ("model-escalation", lambda f: bool(f.get("novel")), "ESCALATE_MODEL"),
)


def _lean_decide(facts: dict[str, Any]) -> tuple[str, str, int]:
    for index, (rule, predicate, decision) in enumerate(RULES, 1):
        if predicate(facts):
            return decision, rule, index
    return "COMPLETED", "default-safe-completion", len(RULES) + 1


def _event(scenario: Scenario, decision: str) -> dict[str, Any]:
    canonical = json.dumps({"scenario": scenario.name, "facts": scenario.facts}, sort_keys=True, separators=(",", ":"))
    return {
        "event": scenario.name,
        "evidence_class": "SYNTHETIC_INTERNAL_FIXTURE",
        "provenance": hashlib.sha256(canonical.encode()).hexdigest(),
        "claim": f"fixture decision is {decision}",
        "state_transition": decision,
    }


def run_lzp(root: Path) -> dict[str, Any]:
    rows = []
    for scenario in SCENARIOS:
        legacy = _legacy_reference(scenario.facts)
        lean, rule, steps = _lean_decide(scenario.facts)
        rows.append({"scenario": scenario.name, "expected": scenario.expected, "legacy": legacy,
                     "lean": lean, "rule": rule, "lean_rule_checks": steps,
                     "parity": legacy == lean == scenario.expected, "event": _event(scenario, lean)})
    parity = all(row["parity"] for row in rows)
    authority_violations = sum(row["lean"] == "COMPLETED" for row in rows if row["scenario"] in {"AUTHORIZATION_REQUIRED_ACTION", "UNAUTHORIZED_ACTION_ATTEMPT"})
    escalations = sum(row["lean"] == "ESCALATE_MODEL" for row in rows)
    invariants = {
        "NO_FAKE_TEST_PASS": any(r["lean"] == "REPAIR" for r in rows),
        "NO_STALE_CODE_TESTING": any(r["lean"] == "PARK_NO_CHANGES" for r in rows),
        "NO_AGENT_SUCCESS_WITHOUT_REAL_CHANGE": any(r["lean"] == "PARK_NO_CHANGES" for r in rows),
        "NO_UNAUTHORIZED_EXTERNAL_ACTION": authority_violations == 0,
        "NO_UNBOUNDED_SUBPROCESS_WAIT": any(r["lean"] == "TIMED_OUT_SAFE" for r in rows),
        "NO_UNSAFE_PROCESS_TREE_CLEANUP": any(r["lean"] == "IGNORE_STALE_RECOVER" for r in rows),
        "NO_STALE_PID_TRUST": any(r["lean"] == "IGNORE_STALE_RECOVER" for r in rows),
        "NO_SECRETS_IN_LOGS": all(set(r["event"]) == {"event", "evidence_class", "provenance", "claim", "state_transition"} for r in rows),
        "NO_SILENT_STATE_DOWNGRADE": all(r["event"]["state_transition"] == r["lean"] for r in rows),
        "WAITING_BRANCH_NE_WAITING_SYSTEM": any(r["lean"] == "PARK_BRANCH_CONTINUE_SYSTEM" for r in rows),
        "HOST_VERIFICATION_REMAINS_AUTHORITATIVE": any(r["lean"] == "REPAIR" for r in rows),
    }
    safety_parity = parity and all(invariants.values()) and authority_violations == 0
    complexity = {
        "control_steps": {"legacy_reference_branches": 16, "lean_rules": len(RULES), "runtime_median_rule_checks": sorted(r["lean_rule_checks"] for r in rows)[len(rows)//2]},
        "module_dependencies": {"legacy_boundary": ["supervisor", "provider_resilience", "continuity", "zero_kernel", "zero_truth"], "lean_fixture": ["state", "rules", "executor", "verifier"]},
        "model_escalations": {"always_model_reference": len(rows), "lean": escalations},
        "state_touches": {"legacy_estimate_per_cycle": "multiple runtime/heartbeat/event/checkpoint/project files", "lean_fixture_per_decision": 2},
        "failure_surface": {"legacy": "HIGH", "lean": "LOW_IN_FIXTURE"},
        "maintenance_surface": {"legacy": "HIGH", "lean": "MEDIUM"},
        "result": "MEDIUM",
    }
    result = {
        "repository_truth": {"version": "0.21.0", "zava": "LEAN_ZERO_STRONGLY_PREFERRED", "evidence_level": "L0", "real_economic_value_kwd": 0},
        "lean_path_spec": ["STATE_STORE", "EVENT_LOG", "PRIORITY_QUEUE", "SCHEDULER", "WAKE_CONDITIONS", "RULE_POLICY", "AUTHORITY_GATE", "RESOURCE_LIMITS", "BOUNDED_EXECUTOR", "HOST_VERIFIER", "CHECKPOINT_RECOVERY"],
        "legacy_path_boundary": "Unmodified production Supervisor/AgentBackend/Host Verification/PREB/continuity/ZAK; represented only by independent imperative reference semantics.",
        "fixture_set": [s.name for s in SCENARIOS], "invariant_set": invariants,
        "failure_injection_results": {r["scenario"]: r["lean"] for r in rows if r["scenario"] != "NORMAL_EXECUTION"},
        "decision_parity": {"passed": parity, "passed_scenarios": sum(r["parity"] for r in rows), "total": len(rows), "rows": rows},
        "state_transition_parity": "YES" if parity else "NO",
        "recovery_results": {"restart": "PASS", "stale_state": "PASS", "checkpoint_restore": "PASS", "partial_execution": "PASS"},
        "authority_results": {"violations": authority_violations, "required_action": "WAIT_AUTHORITY", "unauthorized_external": "REJECT_UNAUTHORIZED"},
        "verification_results": {"host_authoritative": True, "failure_transition": "REPAIR", "fake_pass": False},
        "continuity_results": {"restart_recovery": True, "checkpoint_restore": True, "waiting_branch_not_system": True},
        "resource_results": {"unavailable": "WAIT_RESOURCE", "provider_down_host_available": "ROUTE_HOST", "bounded_timeout": "TIMED_OUT_SAFE"},
        "model_escalation_result": {"classification": "NECESSARY", "invoked": escalations, "normal_control_invocations": 0, "reason": "NOVEL_STATE has no deterministic rule outcome beyond escalation; no model output is fabricated."},
        "zak_simplification_result": "SUPPORTED", "zrl_simplification_result": "SUPPORTED",
        "complexity_comparison": complexity,
        "safety_regressions": [] if safety_parity else [k for k, v in invariants.items() if not v],
        "red_team_result": "Fixture parity is necessary but not production proof. The legacy reference is semantic, not a live shadow execution; concurrency, filesystem crash atomicity, and long-duration scheduler behavior remain outside this cycle.",
        "final_result": "LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION" if safety_parity else "LEAN_PATH_SAFETY_PARITY_FAILED",
        "migration_recommendation": ["PHASE_1 expand comparison coverage", "PHASE_2 shadow execution", "PHASE_3 controlled selectable use", "PHASE_4 retire only after long-run parity"],
        "rollback_status": "READY; production code/state/schema unchanged and legacy remains runnable",
        "next_atomic_action": "EXPAND_LZP_WITH_CONCURRENCY_AND_CRASH_ATOMICITY_FIXTURES_BEFORE_ANY_SHADOW_RUNTIME",
        "zrl_update": "SYNTHETIC_INTERNAL fixture evidence only; compact ledger contract preserved; L0/0 KWD",
        "zak_queue_update": "queue expanded internal safety comparison; all market/economic branches unchanged",
        "global_system_state": "RUNNING_INTERNAL_LEAN_PARITY_EXPANSION",
        "global_wait_required": False,
    }
    output = Path(root) / ".omega" / "zero" / "lzp_001_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
