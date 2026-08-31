from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import CONTRACT_VERSION
from .engine import Engine
from .spec import run_spec
from .store import Store
from .impossibility import build_impossibility_map


def evaluator_session(store: Store, problem_id: str, target_id: str) -> dict[str, Any]:
    """Build a portable review artifact containing conclusions, not private inputs."""
    graph = store.graph(problem_id)
    target = graph_node(graph, target_id)
    engine = Engine(graph)
    source_sha256 = store.export_problem(problem_id)["sha256"]

    def claim(node: dict[str, Any]) -> dict[str, Any]:
        return {"type": node["type"], "role": node["role"], "statement": node["statement"],
                "confidence": node["confidence"], "status": node["status"],
                "evidence_count": len(node.get("evidence", [])),
                "assumptions": node.get("assumptions", []), "uncertainty": node.get("uncertainty", ""),
                "falsifier": node.get("falsifier", "")}

    why, broken, proved, changed = (engine.why(target_id), engine.break_it(),
                                    engine.prove_it(target_id), engine.what_if(target_id, False))
    artifact = {
        "format": "omega.evaluator-session", "format_version": 1, "contract_version": CONTRACT_VERSION,
        "source_problem_sha256": source_sha256,
        "privacy": {"evidence_bodies_included": False, "audit_payloads_included": False,
                    "blind_reveal_included": False, "credential_fields_included": False,
                    "internal_identifiers_included": False},
        "problem": {"title": graph["problem"]["title"], "description": graph["problem"]["description"]},
        "target": claim(target),
        "graph": {"nodes": [claim(node) for node in graph["nodes"]],
                  "relationships": [{"source": graph_node(graph, edge["source_id"])["statement"],
                                     "target": graph_node(graph, edge["target_id"])["statement"],
                                     "type": edge["type"]} for edge in graph["edges"]]},
        "operations": {
            "why": {"reasons": [{"relation": item["relation"], "claim": claim(item["node"])}
                                for item in why["reasons"]],
                    "unresolved_gaps": [claim(node) for node in why["unresolved_gaps"]],
                    "challenges": [claim(item.get("node", item)) for item in why["challenges"]]},
            "break_it": [{"rank": index + 1, "fragility": item["fragility"], "attack": item["attack"],
                          "claim": claim(item["node"])} for index, item in enumerate(broken["attack_order"])],
            "prove_it": {"test_plan": proved["test_plan"], "pass_condition": proved["pass_condition"],
                         "fail_condition": proved["fail_condition"]},
            "what_if_false": {"impacted": [{"via": item["via"], "claim": claim(item["node"])}
                                             for item in changed["impacted"]], "note": changed["note"]},
        },
    }
    canonical = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    artifact["artifact_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return artifact


def analyze_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    context = run_spec(store, spec)
    problem_id = context["imported"]["problem_id"]
    node_id = context["imported"]["node_map"][spec["analysis_target"]]
    graph = store.graph(problem_id); engine = Engine(graph)
    validation = engine.validate(); why = engine.why(node_id); break_it = engine.break_it()
    prove = engine.prove_it(node_id); what_if = engine.what_if(node_id, False)
    unasked_questions = [node for node in graph["nodes"] if node["type"] == "unknown"]
    report = {"format": "omega.analysis-report", "format_version": 1, "contract_version": CONTRACT_VERSION,
              "problem_id": problem_id, "problem": graph["problem"],
              "analysis_target": {"key": spec["analysis_target"], "node": graph_node(graph, node_id)},
              "validation": validation, "why": why, "break_it": break_it, "prove_it": prove,
              "what_if_false": what_if, "unasked_questions": unasked_questions,
              "impossibility_map": build_impossibility_map(graph, node_id),
              "next_actions": [item["attack"] for item in break_it["attack_order"][:3]],
              "audit_events": len(store.list_audit_events(problem_id))}
    return report


def graph_node(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    for node in graph["nodes"]:
        if node["id"] == node_id:
            return node
    raise KeyError(f"node not found in report graph: {node_id}")


def render_markdown(report: dict[str, Any]) -> str:
    target = report["analysis_target"]["node"]
    lines = [f"# OMEGA Analysis — {report['problem']['title']}", "", f"Target: **{target['statement']}**", "",
             f"- Contract: `{report['contract_version']}`", f"- Graph validation: **{report['validation']['valid']}**",
             f"- Audit events: `{report['audit_events']}`", "", "## Unasked questions", ""]
    lines.extend([f"- {node['statement']}" for node in report["unasked_questions"]] or ["- None"])
    lines.extend(["", "## WHY", ""])
    for reason in report["why"]["reasons"]:
        lines.append(f"- `{reason['relation']}` — {reason['node']['statement']}")
    if report["why"]["unresolved_gaps"]:
        lines.extend(["", "Unresolved gaps:"] + [f"- {node['statement']}" for node in report["why"]["unresolved_gaps"]])
    if report["why"]["challenges"]:
        lines.extend(["", "Challenges:"] + [f"- {node['statement']}" for node in report["why"]["challenges"]])
    lines.extend(["", "## BREAK IT", ""])
    for item in report["break_it"]["attack_order"][:5]:
        lines.append(f"- **{item['fragility']:.3f}** — {item['node']['statement']} ({item['attack']})")
    lines.extend(["", "## PROVE IT", "", *[f"- {test}" for test in report["prove_it"]["test_plan"]], "",
                  "## WHAT IF", "", "If the target is false, impacted nodes:"])
    lines.extend([f"- `{item['via']}` — {item['node']['statement']}" for item in report["what_if_false"]["impacted"]] or ["- None"])
    lines.extend(["", "## Next actions", "", *[f"- {action}" for action in report["next_actions"]]])
    return "\n".join(lines) + "\n"
