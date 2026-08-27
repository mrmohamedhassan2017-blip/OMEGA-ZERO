from __future__ import annotations

from typing import Any

from .benchmark import run_all_benchmarks
from .contracts import CONTRACT_VERSION
from .engine import Engine
from .release import run_release_gates
from .self_model import ensure_self_graph
from .store import Store
from .stress import run_concurrency_stress
from .evaluation import run_protocol_gate
from .spec import validate_spec
import json
from pathlib import Path


def run_stability_audit(store: Store) -> dict[str, Any]:
    health = store.database_health()
    graph = ensure_self_graph(store); engine = Engine(graph)
    validation = engine.validate(); benchmarks = run_all_benchmarks(); release = run_release_gates()
    concurrency = run_concurrency_stress()
    evaluation_protocol = run_protocol_gate()
    example_path = Path(__file__).resolve().parent.parent / "examples" / "launch.problem.json"
    try:
        declarative = validate_spec(json.loads(example_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        declarative = {"valid": False, "error": str(exc)}
    goal = next(node for node in graph["nodes"] if node["statement"] == "OMEGA analysis is trustworthy and actionable")
    audit_events = store.list_audit_events(graph["problem"]["id"])
    first = {"why": engine.why(goal["id"]), "break_it": engine.break_it(),
             "prove_it": engine.prove_it(goal["id"]), "what_if": engine.what_if(goal["id"], False)}
    second = {"why": engine.why(goal["id"]), "break_it": engine.break_it(),
              "prove_it": engine.prove_it(goal["id"]), "what_if": engine.what_if(goal["id"], False)}
    boundary_present = any("WOS and Reality Compiler remain excluded" in node["statement"] for node in graph["nodes"])
    gates = [
        {"gate": "database-integrity", "passed": health["healthy"] and health["schema_version"] == 6, "evidence": health},
        {"gate": "self-graph-valid", "passed": validation["valid"], "evidence": validation["summary"]},
        {"gate": "benchmarks", "passed": benchmarks["gate_passed"],
         "evidence": {"ranking": benchmarks["ranking"]["gate_passed"],
                      "taxonomy": benchmarks["taxonomy"]["gate_passed"],
                      "operations": benchmarks["operations"]["passed"],
                      "sensitivity": benchmarks["sensitivity"]["gate_passed"]}},
        {"gate": "portability-recovery", "passed": release["passed"], "evidence": release["summary"]},
        {"gate": "deterministic-operations", "passed": first == second, "evidence": {"operations": list(first)}},
        {"gate": "scope-boundary", "passed": boundary_present, "evidence": {"wos_reality_compiler_excluded": boundary_present}},
        {"gate": "contract-version", "passed": all(value["contract_version"] == CONTRACT_VERSION for value in first.values()),
         "evidence": {"expected": CONTRACT_VERSION}},
        {"gate": "multi-process-writes", "passed": concurrency["passed"],
         "evidence": {"workers": concurrency["workers"], "writes": concurrency["expected_writes"],
                      "database": concurrency["database"]}},
        {"gate": "blind-evaluation-protocol", "passed": evaluation_protocol["passed"],
         "evidence": evaluation_protocol},
        {"gate": "append-only-audit", "passed": bool(audit_events)
                  and [event["sequence"] for event in audit_events] == sorted(event["sequence"] for event in audit_events),
         "evidence": {"events": len(audit_events), "first_action": audit_events[0]["action"] if audit_events else None,
                     "last_action": audit_events[-1]["action"] if audit_events else None}},
        {"gate": "declarative-first-use", "passed": declarative.get("valid", False),
         "evidence": declarative},
    ]
    blockers = [
        "No independently collected user-outcome evidence yet shows that recommendations improve decisions.",
        "No verified blind-evaluation records from an external evaluator have been supplied yet.",
    ]
    core_candidate = all(gate["passed"] for gate in gates)
    return {"core_candidate_passed": core_candidate, "ready_for_v1": core_candidate and not blockers,
            "gates": gates, "summary": {"passed": sum(gate["passed"] for gate in gates), "total": len(gates)},
            "v1_blockers": blockers}
