from __future__ import annotations

from typing import Any

from .contracts import CONTRACT_VERSION
from .engine import Engine


def _node(node_id: str, kind: str, role: str, statement: str, confidence: float,
          evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"id": node_id, "problem_id": "ops", "type": kind, "role": role, "statement": statement,
            "confidence": confidence, "evidence": evidence or [], "status": "open", "created_at": "fixture"}


def reference_graph() -> dict[str, Any]:
    observed = [{"source": "labelled-fixture", "observed_at": "2026-08-27", "method": "reference-case",
                 "reliability": 0.9, "verification_status": "reproduced", "note": None}]
    nodes = [
        _node("launch", "assumption", "prediction", "The launch will succeed", 0.5),
        _node("demand", "unknown", "question", "Will sufficient demand exist?", 0.15),
        _node("budget", "constraint", "limit", "The launch budget is capped", 0.9),
        _node("interviews", "fact", "measurement", "Eight interviews showed interest", 0.85, observed),
        _node("counter", "fact", "observation", "A prior trial had zero conversions", 0.85, observed),
    ]
    edges = [
        {"id": "e1", "problem_id": "ops", "source_id": "launch", "target_id": "demand", "type": "depends_on"},
        {"id": "e2", "problem_id": "ops", "source_id": "launch", "target_id": "budget", "type": "depends_on"},
        {"id": "e3", "problem_id": "ops", "source_id": "interviews", "target_id": "launch", "type": "supports"},
        {"id": "e4", "problem_id": "ops", "source_id": "counter", "target_id": "launch", "type": "contradicts"},
    ]
    return {"problem": {"id": "ops", "title": "Launch decision"}, "nodes": nodes, "edges": edges}


def run_operation_benchmark() -> dict[str, Any]:
    engine = Engine(reference_graph())
    why = engine.why("launch"); break_it = engine.break_it(); prove = engine.prove_it("launch")
    what_if = engine.what_if("demand", False)
    checks = [
        {"operation": "WHY", "claim": "finds prerequisites, supporter, gap, and challenge",
         "passed": {item["node"]["id"] for item in why["reasons"]} == {"demand", "budget", "interviews"}
                   and [node["id"] for node in why["unresolved_gaps"]] == ["demand"]
                   and [node["id"] for node in why["challenges"]] == ["counter"]},
        {"operation": "BREAK_IT", "claim": "selects the labelled weakest bottleneck",
         "passed": break_it["attack_order"][0]["node"]["id"] == "demand"},
        {"operation": "PROVE_IT", "claim": "returns falsifiable plan and prerequisite controls",
         "passed": len(prove["test_plan"]) >= 2
                   and {node["id"] for node in prove["dependencies_to_control"]} == {"demand", "budget"}
                   and "falsify" in prove["test_plan"][0].lower()},
        {"operation": "WHAT_IF", "claim": "propagates a changed prerequisite to its dependent claim",
         "passed": "launch" in [item["node"]["id"] for item in what_if["impacted"]]},
        {"operation": "ALL", "claim": "all results declare the current semantic contract",
         "passed": all(result["contract_version"] == CONTRACT_VERSION for result in (why, break_it, prove, what_if))},
    ]
    return {"contract_version": CONTRACT_VERSION, "checks": checks,
            "passed": all(check["passed"] for check in checks),
            "summary": {"passed": sum(check["passed"] for check in checks), "total": len(checks)}}

