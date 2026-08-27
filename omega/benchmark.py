from __future__ import annotations

from typing import Any

from .engine import Engine
from .ontology import run_taxonomy_benchmark
from .operation_benchmark import run_operation_benchmark
from .sensitivity import run_sensitivity_benchmark


def _node(node_id: str, kind: str, confidence: float, evidence: list | None = None) -> dict[str, Any]:
    return {"id": node_id, "problem_id": "benchmark", "type": kind, "statement": node_id,
            "confidence": confidence, "evidence": evidence or [], "status": "open", "created_at": "fixture"}


def ranking_cases() -> list[dict[str, Any]]:
    reproduced = [{"source": "controlled-test", "observed_at": "2026-08-27", "method": "experiment",
                   "reliability": 0.95, "verification_status": "reproduced", "note": None}]
    return [
        {"name": "unsupported-low-confidence-first",
         "rationale": "An unsupported 0.2 assumption should be attacked before a reproduced 0.8 assumption.",
         "nodes": [_node("expected", "assumption", 0.2), _node("stable", "assumption", 0.8, reproduced)],
         "edges": [], "expected_first": "expected"},
        {"name": "dependency-bottleneck-first",
         "rationale": "At equal confidence, the prerequisite with more direct dependents has higher blast radius.",
         "nodes": [_node("goal1", "assumption", 0.8), _node("goal2", "assumption", 0.8),
                   _node("expected", "unknown", 0.5), _node("isolated", "unknown", 0.5)],
         "edges": [{"source_id": "goal1", "target_id": "expected", "type": "depends_on"},
                   {"source_id": "goal2", "target_id": "expected", "type": "depends_on"}],
         "expected_first": "expected"},
        {"name": "facts-are-not-attack-targets",
         "rationale": "BREAK IT attacks uncertain premises; a fact is checked through PROVE IT/validation.",
         "nodes": [_node("fact", "fact", 0.05, reproduced), _node("expected", "constraint", 0.6)],
         "edges": [], "expected_first": "expected"},
    ]


def run_ranking_benchmark() -> dict[str, Any]:
    results, reciprocal_rank_sum = [], 0.0
    for case in ranking_cases():
        graph = {"problem": {"id": "benchmark", "title": case["name"]},
                 "nodes": case["nodes"],
                 "edges": [{"id": f"e{i}", "problem_id": "benchmark", **edge}
                           for i, edge in enumerate(case["edges"])]}
        order = [item["node"]["id"] for item in Engine(graph).break_it()["attack_order"]]
        rank = order.index(case["expected_first"]) + 1 if case["expected_first"] in order else None
        reciprocal_rank_sum += 1 / rank if rank else 0
        results.append({"name": case["name"], "rationale": case["rationale"], "expected_first": case["expected_first"],
                        "actual_order": order, "rank": rank, "passed": rank == 1})
    total = len(results)
    return {"cases": results, "metrics": {"cases": total,
                                             "top1_accuracy": sum(r["passed"] for r in results) / total,
                                             "mean_reciprocal_rank": round(reciprocal_rank_sum / total, 3)},
            "gate_passed": all(result["passed"] for result in results)}


def run_all_benchmarks() -> dict[str, Any]:
    ranking, taxonomy = run_ranking_benchmark(), run_taxonomy_benchmark()
    operations, sensitivity = run_operation_benchmark(), run_sensitivity_benchmark()
    return {"ranking": ranking, "taxonomy": taxonomy, "operations": operations, "sensitivity": sensitivity,
            "gate_passed": all((ranking["gate_passed"], taxonomy["gate_passed"], operations["passed"],
                                sensitivity["gate_passed"]))}
