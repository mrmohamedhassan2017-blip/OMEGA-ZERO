from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .evidence import evidence_strength
from .ontology import normalize_role
from .contracts import CONTRACT_VERSION
from .scoring import DEFAULT_SCORING_PROFILE, ScoringProfile


class Engine:
    """Deterministic reasoning operations over a Problem/Assumption Graph."""

    def __init__(self, graph: dict[str, Any], scoring_profile: ScoringProfile | None = None) -> None:
        self.graph = graph
        self.scoring_profile = scoring_profile or DEFAULT_SCORING_PROFILE
        self.nodes = {n["id"]: n for n in graph["nodes"]}
        self.outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in graph["edges"]:
            self.outgoing[edge["source_id"]].append(edge)
            self.incoming[edge["target_id"]].append(edge)

    def why(self, node_id: str) -> dict[str, Any]:
        self._require(node_id)
        reasons, challenges, seen = [], [], {node_id}
        queue = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            traversals = []
            traversals.extend((edge, edge["target_id"]) for edge in self.outgoing[current] if edge["type"] == "depends_on")
            traversals.extend((edge, edge["source_id"]) for edge in self.incoming[current] if edge["type"] == "supports")
            for edge, nxt in sorted(traversals, key=lambda item: (item[0]["type"], self.nodes[item[1]]["statement"], item[1])):
                if nxt not in seen:
                    seen.add(nxt)
                    reasons.append({"depth": depth + 1, "relation": edge["type"], "node": self.nodes[nxt]})
                    queue.append((nxt, depth + 1))
        for edge in self.incoming[node_id] + self.outgoing[node_id]:
            if edge["type"] == "contradicts":
                other = edge["source_id"] if edge["target_id"] == node_id else edge["target_id"]
                challenges.append(self.nodes[other])
        challenges.sort(key=lambda node: (node["statement"], node["id"]))
        gaps = [r["node"] for r in reasons if r["node"]["type"] == "unknown"]
        return {"operation": "WHY", "contract_version": CONTRACT_VERSION, "target": self.nodes[node_id],
                "reasons": reasons, "unresolved_gaps": gaps, "challenges": challenges}

    def break_it(self) -> dict[str, Any]:
        ranked = []
        for node in self.nodes.values():
            if node["type"] not in {"assumption", "constraint", "unknown"}:
                continue
            direct_dependents = [e["source_id"] for e in self.incoming[node["id"]] if e["type"] == "depends_on"]
            reachable = set(direct_dependents); queue = deque(direct_dependents)
            while queue:
                current = queue.popleft()
                for edge in self.incoming[current]:
                    if edge["type"] == "depends_on" and edge["source_id"] not in reachable:
                        reachable.add(edge["source_id"]); queue.append(edge["source_id"])
            dependents = len(reachable)
            strength = evidence_strength(node["evidence"])
            confidence_risk = round((1 - node["confidence"]) * self.scoring_profile.confidence_weight, 3)
            dependency_risk = round(min(dependents, self.scoring_profile.dependency_cap) * self.scoring_profile.dependency_weight, 3)
            evidence_risk = round((1 - strength) * self.scoring_profile.evidence_weight, 3)
            fragility = round(confidence_risk + dependency_risk + evidence_risk, 3)
            ranked.append({"node": node, "dependents": dependents, "evidence_strength": strength,
                           "score_components": {"confidence_risk": confidence_risk,
                                                "dependency_risk": dependency_risk,
                                                "evidence_risk": evidence_risk},
                           "fragility": min(fragility, 1.0),
                           "attack": f"Falsify: {node['statement']}"})
        ranked.sort(key=lambda x: (-x["fragility"], -x["dependents"], x["node"]["statement"], x["node"]["id"]))
        return {"operation": "BREAK_IT", "contract_version": CONTRACT_VERSION,
                "scoring_profile": self.scoring_profile.to_dict(), "attack_order": ranked}

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
        dependencies = [self.nodes[e["target_id"]] for e in self.outgoing[node_id] if e["type"] == "depends_on"]
        return {"operation": "PROVE_IT", "contract_version": CONTRACT_VERSION, "target": node,
                "existing_evidence": node["evidence"], "dependencies_to_control": dependencies,
                "test_plan": tests, "pass_condition": "Evidence is reproducible and directly addresses the statement.",
                "fail_condition": "The result contradicts the statement or remains non-observable."}

    def what_if(self, node_id: str, new_value: bool) -> dict[str, Any]:
        node = self._require(node_id)
        impacted, seen = [], {node_id}
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            traversals = []
            traversals.extend((edge, edge["source_id"]) for edge in self.incoming[current] if edge["type"] == "depends_on")
            traversals.extend((edge, edge["target_id"]) for edge in self.outgoing[current] if edge["type"] == "supports")
            for edge in self.incoming[current] + self.outgoing[current]:
                if edge["type"] == "contradicts":
                    traversals.append((edge, edge["source_id"] if edge["target_id"] == current else edge["target_id"]))
            for edge, nxt in sorted(traversals, key=lambda item: (item[0]["type"], self.nodes[item[1]]["statement"], item[1])):
                if nxt not in seen:
                    seen.add(nxt)
                    impacted.append({"node": self.nodes[nxt], "via": edge["type"]})
                    queue.append(nxt)
        return {"operation": "WHAT_IF", "contract_version": CONTRACT_VERSION,
                "changed": node, "hypothetical_truth": new_value,
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
