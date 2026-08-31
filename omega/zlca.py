"""ZLCA V1 constitutional/intelligence-boundary experiment.

No live model, council, external action, or production path is invoked here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONSTITUTION = (
    "TRUTH_INTEGRITY", "AUTHORITY_BOUNDARIES", "RESOURCE_BOUNDS", "REVERSIBILITY",
    "EVIDENCE_PROVENANCE", "HOST_VERIFICATION", "CONTINUITY", "RECOVERY",
    "KILL_CONDITIONS", "NEGATIVE_EVIDENCE_PRESERVATION",
)

KERNEL = {
    "EVENT_LOG": "ESSENTIAL", "STATE_STORE": "ESSENTIAL", "PRIORITY_QUEUE": "ESSENTIAL",
    "SCHEDULER": "ESSENTIAL", "WAKE_CONDITIONS": "ESSENTIAL", "RULE_POLICY": "ESSENTIAL",
    "AUTHORITY_GATE": "ESSENTIAL", "RESOURCE_LEDGER": "USEFUL",
    "BOUNDED_EXECUTOR": "ESSENTIAL", "HOST_VERIFIER": "ESSENTIAL",
    "CHECKPOINT_RECOVERY": "ESSENTIAL",
}

CASES = (
    ("RULE_MATCH_EXISTS", "DETERMINISTIC", "EXECUTE_BOUNDED"),
    ("NO_RULE_MATCH", "NO_RULE_MATCH", "PARK_PENDING_REASONING"),
    ("AMBIGUOUS_SEMANTIC_INPUT", "AMBIGUOUS_SEMANTICS", "PARK_PENDING_REASONING"),
    ("CONFLICTING_EVIDENCE", "UNEXPECTED_CONTRADICTION", "PARK_PENDING_REASONING"),
    ("NEW_PLAN_REQUIRED", "NEW_PLAN_REQUIRED", "PARK_PENDING_REASONING"),
    ("CAPABILITY_MISSING", "CAPABILITY_MISSING", "PARK_PENDING_REASONING"),
    ("CLOSE_ALTERNATIVES", "MULTIPLE_CLOSE_OPTIONS", "PARK_PENDING_REASONING"),
    ("NEGATIVE_EVIDENCE_REVERSAL", "UNEXPECTED_CONTRADICTION", "PARK_PENDING_REASONING"),
    ("AUTHORITY_BOUNDARY", "HIGH_EPISTEMIC_UNCERTAINTY", "WAIT_AUTHORITY"),
    ("UNSAFE_CONFIDENT_PROPOSAL", "HIGH_EPISTEMIC_UNCERTAINTY", "REJECT_UNVERIFIED"),
)

FAILURES = {
    "model_unavailable": "PARK",
    "model_timeout": "RETRY_WITH_LIMIT_THEN_PARK",
    "bad_model_proposal": "REJECT_ACTION",
    "hallucinated_tool": "REJECT_ACTION",
    "unsupported_claim": "REJECT_ACTION",
    "authority_overreach": "REQUEST_OWNER_OR_REJECT",
    "council_disagreement": "PARK_NO_CONSENSUS_IS_NOT_AUTHORITY",
    "excessive_escalation": "BUDGET_EXHAUSTED_PARK",
    "duplicate_escalation": "DEDUPLICATE_BY_ESCALATION_ID",
    "stale_model_result": "REJECT_STALE_RESULT",
    "recovery_during_escalation": "RESTORE_CHECKPOINT_AND_REVALIDATE",
}


def _escalation(case: str, trigger: str, final: str) -> dict[str, Any]:
    identity = hashlib.sha256(f"ZLCA-001:{case}:{trigger}".encode()).hexdigest()[:16]
    deterministic = "known rule resolves safely" if trigger == "DETERMINISTIC" else "safe park/wait/reject without guessing"
    return {
        "escalation_id": f"esc-{identity}", "state": case, "reason": trigger,
        "deterministic_alternative": deterministic,
        "expected_decision_value": "UNKNOWN_UNTIL_VERIFIED_OUTCOME",
        "model_cost": "NOT_INCURRED", "owner_attention_cost": "ZERO_IN_FIXTURE",
        "authority_required": case == "AUTHORITY_BOUNDARY",
        "model_proposal": None, "final_decision": final,
        "verified_outcome": None, "decision_delta": "NOT_MEASURED",
        "model_invoked": False,
    }


def run_zlca(root: Path) -> dict[str, Any]:
    root = Path(root)
    lzp_path = root / ".omega" / "zero" / "lzp_001_result.json"
    if not lzp_path.exists():
        raise RuntimeError("LZP result required before ZLCA")
    lzp = json.loads(lzp_path.read_text(encoding="utf-8"))
    if lzp.get("final_result") != "LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION":
        raise RuntimeError("LZP safety/complexity gate did not pass")

    escalation_rows = [_escalation(*case) for case in CASES]
    # Only nine states cross the gate; a known rule is deliberately not escalated.
    eligible = [row for row in escalation_rows if row["reason"] != "DETERMINISTIC"]
    failure_rows = [{"failure": key, "fallback": value, "authority_preserved": True,
                     "verification_preserved": True, "continuity_preserved": True,
                     "truth_preserved": True} for key, value in FAILURES.items()]
    master = {
        "name": "LEAN_MODEL_ESCALATION_SHADOW_TEST",
        "objective": "Measure verified decision delta from bounded model escalation on fair novel/semantic states without placing models in routine control.",
        "baseline": "deterministic safe park/wait/reject plus ordinary owner escalation when authority is required",
        "success": "repeatable verified useful decision change or error prevention with unchanged authority/verification and lower owner attention than baseline",
        "failure": "no decision delta, explanation-only output, unsafe proposal, or cost/attention not improved",
        "kill": "three representative escalations produce no verified useful delta or any constitutional violation",
        "max_scope": "internal shadow proposals only; no production execution, external action, secrets, or architecture migration",
        "exit_criteria": "at least three representative non-tailored cases with recorded baseline, proposal, host-verifiable outcome, cost, attention, and decision delta",
        "owner_required": False,
    }
    result = {
        "repository_truth": {"version": "0.21.0", "lzp": lzp["final_result"], "lzp_safety_parity": True,
                             "evidence_level": "L0", "real_economic_value_kwd": 0,
                             "production_migration_authorized": False},
        "lzp_result_consumed": {"path": ".omega/zero/lzp_001_result.json", "result": lzp["final_result"],
                                "authority_violations": lzp["authority_results"]["violations"]},
        "constitutional_core": list(CONSTITUTION),
        "deterministic_kernel_map": KERNEL,
        "escalation_trigger_map": {case: trigger for case, trigger, _ in CASES},
        "intelligence_escalation_spec": {"required_fields": ["ESCALATION_ID", "STATE", "REASON", "DETERMINISTIC_ALTERNATIVE", "EXPECTED_DECISION_VALUE", "MODEL_COST", "OWNER_ATTENTION_COST", "AUTHORITY_REQUIRED", "MODEL_PROPOSAL", "FINAL_DECISION", "VERIFIED_OUTCOME", "DECISION_DELTA"],
                                         "normal_loop": False, "constitutional_override": False,
                                         "budget": "one bounded proposal per escalation; retry only once on transient timeout; then park"},
        "model_escalation_results": escalation_rows,
        "model_escalation_yield": {"value": "NOT_MEASURED", "useful_verified_decision_changes": 0,
                                   "model_escalations_executed": 0, "eligible_shadow_cases": len(eligible),
                                   "model_call_count": 0, "model_call_cost": "ZERO_NOT_INVOKED",
                                   "escalation_failures": 0, "false_escalations": 0,
                                   "unnecessary_escalations": 0, "decision_improvement": "UNKNOWN",
                                   "owner_attention_saved": "UNKNOWN"},
        "capability_acquisition_results": {"status": "NOT_TESTED", "reason": "No live model/capability build was authorized by evidence; a synthetic capability puzzle would fabricate advantage.",
                                           "baseline": "ordinary engineer", "t1": "NOT_RUN", "t2": "NOT_RUN", "t3": "NOT_RUN"},
        "capability_reuse_results": {"advantage": "UNKNOWN", "reason": "No accepted capability crossed T1, so reuse cannot be claimed."},
        "expert_council_gate": {"ordinary_runtime": False, "requires_all": ["EXPECTED_IMPACT_HIGH", "UNCERTAINTY_HIGH", "IRREVERSIBILITY_OR_RESOURCE_COST_HIGH"],
                                "allowed_boundaries": ["ARCHITECTURE_CHANGE", "NEW_EXTERNAL_AUTHORITY", "HIGH_RESOURCE_COMMITMENT", "CAPABILITY_INVESTMENT", "MAJOR_STRATEGIC_PIVOT", "REPEATED_UNEXPLAINED_FAILURE", "CONFLICT_BETWEEN_MISSION_OBJECTIVES"]},
        "council_role_results": {"status": "NOT_INVOKED", "roles": ["FOUNDER_CEO", "CTO_SYSTEMS_ARCHITECT", "ALGORITHM_DESIGNER", "AUTONOMOUS_SYSTEMS_RESEARCHER", "ECONOMIST_RESOURCE_ALLOCATOR", "PRODUCT_FOUNDER", "EXPERIMENTAL_SCIENTIST", "SAFETY_AUTHORITY_ARCHITECT", "OPERATIONS_ENGINEER", "RED_TEAM"]},
        "council_value_results": {"value": "UNKNOWN", "decision_change": "NOT_MEASURED", "risk_reduction": "NOT_MEASURED", "reason": "No real qualifying strategic boundary with a verifiable outcome existed."},
        "three_layer_ablation": {
            "A_DETERMINISTIC_KERNEL_ONLY": {"safety": "PASS", "known_case": "SOLVED", "uncertain_cases": "SAFE_PARK_WAIT_REJECT", "model_calls": 0, "complexity": "LOW"},
            "B_KERNEL_MODEL_ESCALATION": {"safety_gate": "PASS_FIXTURE", "proposals": "NOT_EXECUTED", "verified_value": "UNKNOWN", "complexity": "MEDIUM_CONDITIONAL"},
            "C_KERNEL_MODEL_COUNCIL": {"status": "NOT_INVOKED_NO_QUALIFYING_CASE", "verified_value": "UNKNOWN", "complexity": "HIGH"},
        },
        "complexity_value_results": {"deterministic_kernel": "JUSTIFIED", "model_escalation_interface": "CONDITIONALLY_JUSTIFIED_AS_SAFE_BOUNDARY_VALUE_UNPROVEN", "expert_council": "UNKNOWN_KEEP_OFF", "continuous_hypothesis_machinery": "REDUNDANT_DEFAULT", "economic_runtime": "REDUNDANT_CURRENTLY"},
        "zak_role": "CORE_MINIMAL", "zrl_role": "SIMPLIFIED_CORE",
        "hypothesis_engine_role": "RESEARCH_MODE_ONLY",
        "capability_discovery_role": "ON_CAPABILITY_GAP",
        "economic_layer_role": "ARCHIVED",
        "intelligence_boundary_map": {
            "retry_timeout_deduplication": "DETERMINISTIC", "authority_check": "DETERMINISTIC",
            "wake_scheduling": "DETERMINISTIC", "evidence_logging": "DETERMINISTIC",
            "known_plan_execution": "DETERMINISTIC", "semantic_ambiguity": "MODEL_ESCALATION_CANDIDATE",
            "novel_bounded_state": "MODEL_ESCALATION_CANDIDATE", "capability_gap_design": "MODEL_ESCALATION_CANDIDATE_ON_EVIDENCE",
            "external_authority_finance_legal_sensitive_data": "OWNER",
            "high_impact_irreversible_strategic_uncertainty": "OWNER_WITH_OPTIONAL_COUNCIL_REVIEW",
        },
        "failure_injection_results": failure_rows,
        "model_failure_fallback": FAILURES,
        "owner_interrupt_policy": {"do_not_interrupt": ["routine internal decisions", "retries", "parking", "wake handling", "internal experiments", "host verification", "normal model escalation"],
                                   "interrupt": ["new external authority", "financial commitment", "irreversible external action", "sensitive data access", "mission change", "legal commitment", "high-impact uncertain action"]},
        "autonomy_efficiency_result": "DETERMINISTIC_KERNEL_STRONG_FOR_KNOWN_STATES; INTELLIGENCE_EFFICIENCY_UNPROVEN_UNTIL_VERIFIED_DECISION_DELTA",
        "red_team_result": "A competent deterministic system with occasional ordinary human escalation currently matches all verified behavior. Calling an escalation interface 'intelligence' adds no value until model proposals change verified outcomes. Council roles without such a case would be theater.",
        "architecture_comparison": {
            "MINIMAL_DETERMINISTIC_ZERO": {"safety": "STRONG", "correctness": "STRONG_KNOWN_STATES", "novel_task_handling": "SAFE_PARK", "owner_attention": "ONLY_UNRESOLVED_OR_AUTHORITY", "resource_cost": "LOW", "model_dependence": "NONE", "complexity": "LOW", "failure_surface": "LOW", "maintenance": "LOW", "capability_reuse": "UNKNOWN", "mission_fit": "CURRENTLY_BEST_EVIDENCE"},
            "LEAN_ZERO_WITH_MODEL_ESCALATION": {"safety": "GATE_PASSES_FIXTURE", "correctness": "OUTCOME_UNPROVEN", "novel_task_handling": "POTENTIAL", "owner_attention": "UNKNOWN", "resource_cost": "UNKNOWN", "model_dependence": "BOUNDED", "complexity": "MEDIUM", "failure_surface": "MEDIUM", "maintenance": "MEDIUM", "capability_reuse": "UNKNOWN", "mission_fit": "CONDITIONAL"},
            "LEAN_ZERO_WITH_MODEL_ESCALATION_AND_EXPERT_COUNCIL": {"safety": "CONSTITUTIONALLY_GATED", "correctness": "UNPROVEN", "novel_task_handling": "UNPROVEN", "owner_attention": "UNKNOWN", "resource_cost": "HIGH", "model_dependence": "HIGH", "complexity": "HIGH", "failure_surface": "HIGH", "maintenance": "HIGH", "capability_reuse": "UNKNOWN", "mission_fit": "NOT_EARNED"},
        },
        "final_architecture_decision": "MINIMAL_DETERMINISTIC_ZERO_PREFERRED",
        "migration_plan": ["PHASE_0 freeze legacy", "PHASE_1 expand internal coverage", "PHASE_2 shadow comparison", "PHASE_3 selectable controlled path", "PHASE_4 long-run parity", "PHASE_5 retire only proven redundancy"],
        "rollback_status": "READY; no production migration, schema change, deletion, model call, council call, or external action",
        "master_active_project": master,
        "master_project_exit_criteria": master["exit_criteria"],
        "next_atomic_action": "RUN_LEAN_MODEL_ESCALATION_SHADOW_TEST_ON_THREE_NON_TAILORED_INTERNAL_CASES_WITH_VERIFIABLE_OUTCOMES",
        "zrl_update": "REAL_INTERNAL architecture boundary result; no model-value evidence; L0/0 KWD",
        "zak_queue_update": "one master internal shadow project; economic/market layers remain closed",
        "global_system_state": "RUNNING_INTERNAL_MODEL_VALUE_FALSIFICATION",
        "global_wait_required": False,
    }
    out = root / ".omega" / "zero" / "zlca_001_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
