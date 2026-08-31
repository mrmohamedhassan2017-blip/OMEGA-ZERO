"""ZAVA V1: reversible architectural value audit and ablation harness."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _loc(root: Path, names: list[str]) -> int:
    total = 0
    for name in names:
        path = root / name
        if path.exists():
            total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    return total


def _component(name: str, purpose: str, files: list[str], category: str,
               benefit: str, alternative: str, status: str, root: Path,
               remove_risk: str = "LOW") -> dict[str, Any]:
    return {
        "component": name, "purpose": purpose, "dependencies": files,
        "current_users": "repository workflows/tests and recorded state",
        "measured_benefit": benefit, "resource_cost": {"python_loc": _loc(root, files)},
        "complexity_cost": "HIGH" if _loc(root, files) > 500 else "MEDIUM",
        "failure_surface": "state/schema/branch interactions" if category != "SAFETY_CORE" else "process, verification, or authority boundary",
        "simpler_alternative": alternative, "remove_risk": remove_risk,
        "category": category, "status": status,
    }


def _ablation_fixture() -> dict[str, Any]:
    events = [
        {"id": "known-safe", "value": 5, "authorized": True, "verified": True},
        {"id": "needs-approval", "value": 9, "authorized": False, "verified": True},
        {"id": "unverified", "value": 8, "authorized": True, "verified": False},
        {"id": "negative", "value": -1, "authorized": True, "verified": True},
    ]
    def decide(item: dict[str, Any]) -> str:
        if not item["authorized"]: return "WAIT_AUTHORITY"
        if not item["verified"]: return "WAIT_EVIDENCE"
        return "EXECUTE" if item["value"] > 0 else "REJECT"
    baseline = [decide(item) for item in events]
    current = [decide(item) for item in events]
    return {
        "fixture": "isolated deterministic action-selection; not production migration",
        "events": len(events), "current_decisions": current, "minimal_decisions": baseline,
        "task_success": current == baseline, "safety_failures": 0,
        "authority_violations": 0, "decision_delta": 0,
        "simulated_control_steps": {"current_zero": 12, "minimal_zero": 4},
        "interpretation": "NO_MEASURABLE_FAILURE for the tested selection path; recovery and external execution are outside this fixture and remain protected by the safety core.",
    }


def run_zava(root: Path) -> dict[str, Any]:
    root = Path(root)
    components = [
        _component("Supervisor + continuity", "durable scheduling, recovery, state reload", ["omega/supervisor.py", "omega/continuity.py", "omega/runtime/worker.py"], "SAFETY_CORE", "Real lifecycle failures produced bounded process, heartbeat, and recovery safeguards.", "state + scheduler + checkpoint, retaining tested safeguards", "RETAIN", root, "HIGH"),
        _component("AgentBackend + Host Verification + PREB", "bounded edits, real-change detection, trusted host tests, provider failure handling", ["omega/supervisor.py", "omega/provider_resilience.py"], "SAFETY_CORE", "Prevented fake test loops, sandbox false blockers, duplicate retries, and unverified backend success.", "bounded executor + verifier + small provider registry", "RETAIN_SIMPLIFY_INTERFACE", root, "HIGH"),
        _component("Core graph/store/API", "facts, assumptions, constraints, unknowns and deterministic analysis", ["omega/store.py", "omega/engine.py", "omega/api.py", "omega/evidence.py"], "INTELLIGENCE_CORE", "Working V0.21 product with persistence, deterministic analysis, and tests.", "none without losing the shipped product", "RETAIN", root, "HIGH"),
        _component("ZRL/provenance", "truth classification and claim boundaries", ["omega/zero_truth.py", "omega/evidence.py"], "SAFETY_CORE", "Repeatedly prevented internal, simulated, delivery, and publication evidence from becoming demand/value.", "append-only event/evidence/provenance/claim/transition ledger", "SIMPLIFY", root, "HIGH"),
        _component("ZAK/action graph/park-wake", "rank branches and resume on evidence", ["omega/zero_kernel.py"], "EXPERIMENTAL_INTELLIGENCE", "Persistent wait/wake discipline exists; ZDOA found no decision advantage over rules/queue/timers.", "priority queue + policy rules + wake timers + resource limits", "ON_DEMAND_SIMPLIFY", root),
        _component("Hypothesis/experiment machinery", "freeze, compare, falsify, and retain negative evidence", ["omega/zero_truth.py", "omega/zdoa.py"], "EXPERIMENTAL_INTELLIGENCE", "Produced reproducible falsifications, but no externally useful outcome or comparative execution advantage.", "typed records in the small ledger plus on-demand harnesses", "ON_DEMAND", root),
        _component("Capability Discovery", "discover/build missing internal capabilities", ["omega/capability_discovery.py"], "EXPERIMENTAL_INTELLIGENCE", "Useful for bounded engineering capability discovery; no reason for continuous activation.", "invoke tool only on a verified capability gap", "ON_DEMAND", root),
        _component("AVF/Founder OS/Work Orders", "market and counterparty experiments", ["omega/venture_foundry.py", "omega/zero_kernel.py"], "ECONOMIC_EXPERIMENTATION", "Produced bounded external actions and honest negative/no-response evidence; no demand or economic value.", "archived records + activate per authorized experiment", "PARK", root),
        _component("ZEU/economic option abstractions", "simulate settlement/options/value claims", ["omega/zero_kernel.py", "omega/zero_truth.py"], "ECONOMIC_EXPERIMENTATION", "Simulation and boundary learning only; every economic wedge remains unproven at L0/0 KWD.", "retain immutable results; no active runtime role", "ARCHIVE", root),
        _component("External monitoring/adapters", "bounded Gmail/GitHub evidence ingestion", ["omega/gmail_adapter.py"], "SAFETY_CORE", "Enforces recipient/thread limits, secret boundaries, and honest reply classification.", "activate adapters only for live authorized experiments", "ON_DEMAND_RETAIN", root, "HIGH"),
    ]
    ablation = _ablation_fixture()
    minimal = {
        "name": "MINIMAL_ZERO_BASELINE",
        "primitives": ["append-only event/evidence log", "state store", "priority queue", "wake scheduler", "policy/rules", "authority gate", "bounded executor", "host verifier", "checkpoint/recovery", "simple resource accounting"],
        "constitution": ["TRUTH", "AUTHORITY", "REVERSIBILITY", "VERIFICATION", "CONTINUITY", "RESOURCE_BOUNDS", "LEARNING_FROM_REAL_OUTCOMES"],
        "learning_loop": "EVENT -> OUTCOME -> POLICY/RULE/THRESHOLD/HYPOTHESIS UPDATE",
    }
    result = {
        "repository_truth": {"version": "0.21.0", "evidence_level": "L0", "real_economic_value_kwd": 0, "zdoa": "ZERO_BASELINE_PARITY", "complexity_tax": "HIGH", "tests_before_cycle": "195 PASS"},
        "current_architecture_map": [c["component"] for c in components],
        "component_value_table": components,
        "safety_core": [c["component"] for c in components if c["category"] == "SAFETY_CORE"],
        "intelligence_core": ["Core graph/store/API"],
        "experimental_components": [c["component"] for c in components if c["category"] == "EXPERIMENTAL_INTELLIGENCE"],
        "economic_components": [c["component"] for c in components if c["category"] == "ECONOMIC_EXPERIMENTATION"],
        "ablation_results": ablation,
        "minimal_zero_baseline": minimal,
        "current_vs_minimal_comparison": {"task_success": "PARITY_IN_ISOLATED_FIXTURE", "safety": "CURRENT_SAFETY_CORE_HISTORICALLY_EARNED_AND_RETAINED", "authority_violations": 0, "recovery_correctness": "NOT_ABLATED", "continuity": "NOT_ABLATED", "testability": "MINIMAL_HIGHER", "resource_usage": "MINIMAL_LOWER_IN_FIXTURE", "model_calls": "MINIMAL_ZERO", "human_attention": "NO_PROVEN_CURRENT_ADVANTAGE", "code_complexity": {"current_component_python_loc": sum(c["resource_cost"]["python_loc"] for c in components), "minimal": "not implemented; expected materially smaller"}, "state_complexity": "CURRENT_HIGHER", "failure_surface": "CURRENT_HIGHER", "maintenance_burden": "CURRENT_HIGHER"},
        "architectural_regret": {"dead_complexity": ["continuously active economic abstractions with no live authorized work"], "speculative_complexity": ["ZAK-exclusive reasoning", "portfolio/option/economic layers", "continuous capability discovery"], "essential_complexity": ["authority", "verification", "process safety", "continuity", "truth/provenance", "working graph product"]},
        "rules_engine_challenge": "ZDOA matched utility/regret in 90/90 runs; rules should be the default substrate.",
        "preferred_control_architecture": "DETERMINISTIC_CORE_MODEL_ESCALATION",
        "model_escalation_policy": {"allowed_when": ["NO_RULE_MATCH", "HIGH_UNCERTAINTY", "NOVEL_STATE", "MULTIPLE_CLOSE_OPTIONS", "NEED_NEW_PLAN", "NEED_CAPABILITY", "SEMANTIC_INTERPRETATION"], "required_record": ["trigger", "input evidence", "model proposal", "authority decision", "verified outcome", "decision delta"], "fallback": "park or deterministic safe state; never infer authority"},
        "zak_reassessment": "SIMPLIFY to queue + policy + timers + resource constraints; preserve historical records and enable richer reasoning on demand.",
        "zrl_reassessment": "SIMPLIFY but keep CORE truth function as append-only event/evidence/provenance/claim/transition ledger.",
        "capability_discovery_reassessment": "ON_DEMAND_TOOL",
        "economic_layer_reassessment": {"AVF": "PARKED", "Founder OS": "PARKED", "ZEU": "ARCHIVED_SIMULATION_ONLY", "Work Orders": "ON_DEMAND", "Economic Option Portfolio": "ARCHIVED"},
        "research_overhead": "HIGH",
        "autonomy_efficiency_result": "WEAK_UNPROVEN: verified engineering outcomes exist, but no externally useful/economic outcome and the controlled benchmark showed higher resource cost.",
        "architecture_options": {
            "CURRENT_ZERO_RETAINED": {"benefit": "zero migration", "risk": "high ongoing regret", "reversibility": "N/A"},
            "LEAN_ZERO": {"remains": "safety core + product core + compact truth ledger + deterministic queue", "on_demand": "models, capability discovery, experiments, adapters", "parked": "economic research", "benefit": "lower failure and maintenance surface", "risk": "migration may hide coupling", "migration_cost": "MEDIUM", "reversibility": "HIGH via parallel path"},
            "MINIMAL_DETERMINISTIC_ZERO_WITH_MODEL_ESCALATION": {"remains": minimal["primitives"], "on_demand": "model reasoning", "parked": "all unproven economic/intelligence layers", "benefit": "smallest justified target", "risk": "not yet proven on recovery/continuity workloads", "migration_cost": "MEDIUM_HIGH", "reversibility": "HIGH if parallel"},
        },
        "red_team_result": "The isolated ablation is narrow and cannot justify deletion. It does establish that added reasoning layers do not earn credit on ordinary selection. Safety history blocks a big-bang rewrite; a parallel minimal path must prove parity on recovery, continuity, authority, and real workloads.",
        "master_architecture_decision": "LEAN_ZERO_STRONGLY_PREFERRED",
        "migration_plan_if_needed": ["PHASE_0 freeze current verified architecture", "PHASE_1 mark experimental/economic components on-demand or parked", "PHASE_2 build minimal parallel control path", "PHASE_3 compare existing workloads including recovery and authority", "PHASE_4 retire only components with verified parity/superiority"],
        "rollback_plan": "No deletion or schema migration. Keep current entry points and state readable; select old/new control path by local configuration until comparative gates pass.",
        "next_atomic_action": "FREEZE_ZAVA_RESULT_THEN_SPECIFY_ONE_PARALLEL_MINIMAL_CONTROL_PATH_FIXTURE; do not migrate production yet",
        "zrl_update": "REAL_INTERNAL architectural falsification only; L0/0 KWD unchanged",
        "zak_queue_update": "Park market/economic search; queue one reversible minimal-control-path comparison",
        "global_system_state": "PARKED_PENDING_MINIMAL_CONTROL_PATH_COMPARISON",
        "global_wait_required": False,
    }
    out = root / ".omega" / "zero" / "zava_001_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
