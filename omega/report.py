from __future__ import annotations

from typing import Any

from .contracts import CONTRACT_VERSION
from .engine import Engine
from .spec import run_spec
from .store import Store


def analyze_spec(store: Store, spec: dict[str, Any]) -> dict[str, Any]:
    context = run_spec(store, spec)
    problem_id = context["imported"]["problem_id"]
    node_id = context["imported"]["node_map"][spec["analysis_target"]]
    graph = store.graph(problem_id); engine = Engine(graph)
    validation = engine.validate(); why = engine.why(node_id); break_it = engine.break_it()
    prove = engine.prove_it(node_id); what_if = engine.what_if(node_id, False)
    report = {"format": "omega.analysis-report", "format_version": 1, "contract_version": CONTRACT_VERSION,
              "problem_id": problem_id, "problem": graph["problem"],
              "analysis_target": {"key": spec["analysis_target"], "node": graph_node(graph, node_id)},
              "validation": validation, "why": why, "break_it": break_it, "prove_it": prove,
              "what_if_false": what_if,
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
             f"- Audit events: `{report['audit_events']}`", "", "## WHY", ""]
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
