from __future__ import annotations

from typing import Any

from .contracts import CONTRACT_VERSION


def build_impossibility_map(graph: dict[str, Any], target_id: str | None = None) -> dict[str, Any]:
    """Build a deterministic, explainable map of what makes a target hard."""
    nodes = graph.get("nodes", [])
    target = next((n for n in nodes if n["id"] == target_id), None) if target_id else None
    if target is None and nodes:
        target = next((n for n in nodes if n["type"] == "assumption"), nodes[0])
    weights = {"constraint": 1.0, "assumption": 0.85, "unknown": 0.7, "fact": 0.25}
    blockers = []
    for node in nodes:
        if target and node["id"] == target["id"]:
            continue
        severity = round((1.0 - float(node.get("confidence", 0.5))) * weights.get(node["type"], 0.5), 6)
        if node["type"] in {"constraint", "assumption", "unknown"}:
            blockers.append({"node": node, "category": node["type"], "severity": severity,
                             "change_question": f"What must change about: {node['statement']}?"})
    blockers.sort(key=lambda item: (-item["severity"], item["node"]["id"]))
    dependents = {node["id"]: 0 for node in nodes}
    for edge in graph.get("edges", []):
        if edge.get("type") == "depends_on":
            dependents[edge["target_id"]] = dependents.get(edge["target_id"], 0) + 1
    for item in blockers:
        item["dependent_count"] = dependents.get(item["node"]["id"], 0)
    miracle = max(blockers, key=lambda item: (item["dependent_count"], item["severity"], item["node"]["id"])) if blockers else None
    score = round(sum(item["severity"] for item in blockers) / max(len(blockers), 1), 6)
    return {"format": "omega.impossibility-map", "format_version": 1,
            "contract_version": CONTRACT_VERSION, "target": target,
            "current_reality": {"nodes": len(nodes), "edges": len(graph.get("edges", [])),
                                 "validated": not bool(graph.get("issues"))},
            "blockers": blockers, "impossibility_score": score,
            "score_explanation": "mean weighted uncertainty: (1-confidence) × category weight",
            "minimum_reality_change": blockers[0]["change_question"] if blockers else None,
            "one_miracle": {"statement": miracle["node"]["statement"], "dependent_count": miracle["dependent_count"],
                            "change_question": miracle["change_question"]} if miracle else None}
