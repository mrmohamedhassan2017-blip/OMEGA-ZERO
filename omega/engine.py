from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class Engine:
    """Deterministic reasoning operations over a Problem/Assumption Graph."""

    def __init__(self, graph: dict[str, Any]) -> None:
        self.graph = graph
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in graph["edges"]:
            self.outgoing[edge["source_id"]].append(edge)
            self.incoming[edge["target_id"]].append(edge)

    def why(self, node_id: str) -> dict[str, Any]:
        self._require(node_id)
        reasons, seen = [], {node_id}
        queue = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            for edge in self.outgoing[current]:
                if edge["type"] not in {"depends_on", "supports"}:
                    continue
                nxt = edge["target_id"]
                if nxt not in seen:
                    seen.add(nxt)
                    reasons.append({"depth": depth + 1, "relation": edge["type"], "node": self.nodes[nxt]})
                    queue.append((nxt, depth + 1))
        gaps = [r["node"] for r in reasons if r["node"]["type"] == "unknown"]
        return {"operation": "WHY", "target": self.nodes[node_id], "reasons": reasons, "unresolved_gaps": gaps}

    def break_it(self) -> dict[str, Any]:
        ranked = []
        for node in self.nodes.values():
            if node["type"] not in {"assumption", "constraint", "unknown"}:
                continue
            dependents = len([e for e in self.incoming[node["id"]] if e["type"] == "depends_on"])
            evidence_penalty = 0 if node["evidence"] else 0.25
            fragility = round((1 - node["confidence"]) * 0.6 + min(dependents, 5) * 0.08 + evidence_penalty, 3)
            ranked.append({"node": node, "dependents": dependents, "fragility": min(fragility, 1.0),
                           "attack": f"Falsify: {node['statement']}"})
        ranked.sort(key=lambda x: (-x["fragility"], -x["dependents"], x["node"]["id"]))
        return {"operation": "BREAK_IT", "attack_order": ranked}

    def prove_it(self, node_id: str) -> dict[str, Any]:
        node = self._require(node_id)
        tests = []
        if node["type"] == "fact":
            tests.append("Verify the source, date, scope, and reproducibility of the evidence.")
        elif node["type"] == "assumption":
            tests.extend(["Define an observable result that would falsify this assumption.",
                          "Run the cheapest controlled test and record raw evidence."])
        elif node["type"] == "constraint":
            tests.extend(["Identify who or what imposes this limit.", "Test the boundary and document exceptions."])
        else:
            tests.extend(["Turn the unknown into a measurable question.", "Collect the smallest decisive dataset."])
        return {"operation": "PROVE_IT", "target": node, "existing_evidence": node["evidence"],
                "test_plan": tests, "pass_condition": "Evidence is reproducible and directly addresses the statement.",
                "fail_condition": "The result contradicts the statement or remains non-observable."}

    def what_if(self, node_id: str, new_value: bool) -> dict[str, Any]:
        node = self._require(node_id)
        impacted, seen = [], {node_id}
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            for edge in self.incoming[current]:
                if edge["type"] not in {"depends_on", "supports", "contradicts"}:
                    continue
                nxt = edge["source_id"]
                if nxt not in seen:
                    seen.add(nxt)
                    impacted.append({"node": self.nodes[nxt], "via": edge["type"]})
                    queue.append(nxt)
        return {"operation": "WHAT_IF", "changed": node, "hypothetical_truth": new_value,
                "impacted": impacted, "note": "Impact is structural, not a claim of causal certainty."}

    def validate(self) -> dict[str, Any]:
        issues = []
        for node in self.nodes.values():
            if node["type"] == "fact" and not node["evidence"]:
                issues.append({"severity": "error", "code": "FACT_WITHOUT_EVIDENCE", "node_id": node["id"]})
            if node["type"] == "unknown" and node["status"] in {"supported", "falsified"}:
                issues.append({"severity": "warning", "code": "UNKNOWN_HAS_TRUTH_STATUS", "node_id": node["id"]})
            if node["confidence"] < 0 or node["confidence"] > 1:
                issues.append({"severity": "error", "code": "INVALID_CONFIDENCE", "node_id": node["id"]})
        orphan_ids = {node_id for node_id in self.nodes if not self.outgoing[node_id] and not self.incoming[node_id]}
        for node_id in sorted(orphan_ids):
            issues.append({"severity": "warning", "code": "ORPHAN_NODE", "node_id": node_id})
        return {"valid": not any(i["severity"] == "error" for i in issues), "issues": issues,
                "summary": {"nodes": len(self.nodes), "edges": len(self.graph["edges"]), "issues": len(issues)}}

    def _require(self, node_id: str) -> dict[str, Any]:
        if node_id not in self.nodes:
            raise KeyError(f"node not found in graph: {node_id}")
        return self.nodes[node_id]
