from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .engine import Engine
from .ontology import DEFAULT_ROLES
from .scoring import ScoringProfile

PROFILES = [
    ScoringProfile(),
    ScoringProfile("confidence-heavy", 0.70, 0.04, 0.18),
    ScoringProfile("dependency-heavy", 0.40, 0.15, 0.20),
    ScoringProfile("evidence-heavy", 0.35, 0.05, 0.55),
]


def load_cases() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parent / "fixtures" / "ranking_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _graph(case: dict[str, Any]) -> dict[str, Any]:
    nodes = [{**node, "problem_id": case["name"], "role": DEFAULT_ROLES[node["type"]],
              "evidence": [], "status": "open", "created_at": "fixture"} for node in case["nodes"]]
    edges = [{**edge, "id": f"e{index}", "problem_id": case["name"]}
             for index, edge in enumerate(case["edges"])]
    return {"problem": {"id": case["name"], "title": case["name"]}, "nodes": nodes, "edges": edges}


def run_sensitivity_benchmark() -> dict[str, Any]:
    cases, results = load_cases(), []
    for profile in PROFILES:
        case_results, reciprocal_sum = [], 0.0
        for case in cases:
            order = [item["node"]["id"] for item in Engine(_graph(case), profile).break_it()["attack_order"]]
            rank = order.index(case["expected_first"]) + 1
            reciprocal_sum += 1 / rank
            case_results.append({"case": case["name"], "domain": case["domain"],
                                 "expected_first": case["expected_first"], "actual_order": order,
                                 "rank": rank, "passed": rank == 1})
        results.append({"profile": profile.to_dict(), "cases": case_results,
                        "top1_accuracy": sum(item["passed"] for item in case_results) / len(case_results),
                        "mean_reciprocal_rank": round(reciprocal_sum / len(case_results), 3)})
    robust = [case["name"] for case in cases if all(
        next(item for item in result["cases"] if item["case"] == case["name"])["passed"] for result in results)]
    return {"fixture_source": "omega/fixtures/ranking_cases.json", "profiles": results,
            "robust_cases": robust, "metrics": {"cases": len(cases), "profiles": len(PROFILES),
                                                   "robust_case_rate": len(robust) / len(cases)},
            "gate_passed": len(robust) == len(cases)}
