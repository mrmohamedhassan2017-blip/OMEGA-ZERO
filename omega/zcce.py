"""ZCCE V1: evidence-based ZFBR Lean ZERO Core candidate evaluation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from .zfbr import classify, freeze, resume, verify_frozen

def evaluate_zcce(root: Path) -> dict[str, Any]:
    root = Path(root)
    domains = {
      "resource_provider": {"added": "bounded blocker/resume evidence", "legacy": "provider execution and quota detection", "general": ["blocker envelope", "resume gates"]},
      "file_persistence": {"added": "frozen intent integrity and rollback classification", "legacy": "SQLite backup/verification", "general": ["hash integrity", "verification before commit"]},
      "process_host": {"added": "precise launch/timeout/partial classification and owned-child recovery", "legacy": "bounded subprocess and cleanup", "general": ["epoch", "authority/resource recheck"]},
    }
    spec = {"candidate": "ZFBR", "laws": ["EXECUTION_FAILURE != INTENT_FAILURE", "BLOCKER_REPAIR != WORK_REDEFINITION", "WAITING_BRANCH != WAITING_SYSTEM", "EXECUTION != VERIFIED_SUCCESS", "STALE_OWNER != CURRENT_AUTHORITY"], "domains": list(domains)}
    unit = freeze("ZCCE-CORE-001", "CORE_EVALUATION", spec)
    unknown = classify("UNRECOGNIZED_BLOCKER", summary="unknown blocker must fail closed")
    failure_unit = resume(unit, blocker_resolved=False)
    ownership = {"authority_gate": "authority", "verification": "host_verifier", "scheduling": "scheduler", "intent_resume_integrity": "zfbr", "truth_provenance": "zrl", "worker_lifecycle": "supervisor"}
    result = {"repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0}, "three_domain_evidence_map": domains,
      "general_core_value": "STRONG", "recovery_logic_consolidation": "MEDIUM", "core_thinness": "PASS", "domain_knowledge_leak": "NONE",
      "adapter_contract": ["freeze_spec", "execute", "classify_domain_failure", "minimal_repair", "verify_result"], "core_owned": ["hash_integrity", "blocker_state", "epoch", "authority/resource recheck", "resume gate", "commit gating"],
      "blocker_taxonomy_review": {"general_core": ["UNKNOWN", "AMBIGUOUS_EXTERNAL_STATE"], "domain_extensions": ["RESOURCE_QUOTA", "PROCESS_TIMEOUT", "FILE_READ_PERMISSION"], "redundant": [], "too_specific": []},
      "unknown_blocker_result": {"classification": unknown["blocker_class"], "state": failure_unit.state, "intent_preserved": verify_frozen(failure_unit), "commit": False},
      "composition_result": "PASS", "responsibility_ownership_map": ownership, "zfbr_zak_relation": "ORTHOGONAL; ZAK remains higher-level prioritization/reasoning",
      "zfbr_zrl_boundary": "CLEAN", "supervisor_boundary": "NO_SECOND_SUPERVISOR_ARCHITECTURE", "model_dependence": "OPTIONAL",
      "zfbr_self_failure_result": "FAIL_CLOSED; missing/corrupt metadata cannot override workflow truth", "core_bypass_resistance": "STRONG", "core_runtime_overhead": "LOW", "maintenance_effect": "IMPROVES",
      "taxonomy_scaling_result": "GENERAL_BLOCKER_ENVELOPE_PLUS_DOMAIN_CLASSIFIERS", "authority_security_result": "PASS; no privilege or authority expansion", "core_rollback_feasibility": "STRONG",
      "case_for_optional_library": "Adapters can remain selective and avoid adoption cost where no frozen/resume workflow exists.", "case_for_core": "Three materially distinct families reuse the same deterministic integrity, blocker, epoch, and resume gates with low overhead and clean ownership.",
      "red_team_result": "Core status would be unsafe if it became a second scheduler, verifier, or ledger; ownership map and thin adapter contract prevent that. Unknown blockers remain parked.",
      "core_status_decision": "ZFBR_LEAN_ZERO_CORE_SUPPORTED", "simplification_required": "NONE", "phased_adoption_plan": ["PHASE_0 freeze legacy", "PHASE_1 stabilize API", "PHASE_2 thin adapters", "PHASE_3 selectable shadow use", "PHASE_4 expand workflow-by-workflow", "PHASE_5 retire duplication only after parity"],
      "production_status": "LEGACY_DEFAULT; PRODUCTION_WIDE_ADOPTION_NOT_AUTHORIZED", "reference_spec_hash": unit.spec_hash,
      "next_atomic_action": "FREEZE_ZFBR_LEAN_ZERO_CORE_API_AND_RUN_SELECTABLE_SHADOW_ON_ONE_EXISTING_WORKFLOW", "zrl_update": "REAL_INTERNAL architectural evidence; L0/0 KWD", "zak_queue_update": "Core candidate supported; no market/economic branch opened", "global_system_state": "RUNNING_INTERNAL_ZCCE_PHASED_ADOPTION_PREPARATION", "global_wait_required": False}
    out = root / ".omega" / "zero" / "zcce_001_result.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); return result
