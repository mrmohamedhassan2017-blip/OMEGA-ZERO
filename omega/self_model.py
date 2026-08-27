from __future__ import annotations

from typing import Any

from .engine import Engine
from .store import Store

TITLE = "OMEGA Core can produce trustworthy, actionable analysis"


def ensure_self_graph(store: Store) -> dict[str, Any]:
    existing = store.find_problem(TITLE)
    if existing:
        return store.graph(existing["id"])

    problem = store.create_problem(TITLE, "OMEGA V0.x applies its own reasoning model to its design and claims.")
    pid = problem["id"]
    nodes = {
        "goal": store.add_node(pid, "assumption", "OMEGA analysis is trustworthy and actionable", 0.25),
        "types": store.add_node(pid, "assumption", "Four node types capture the distinctions needed by real problems", 0.35),
        "semantics": store.add_node(pid, "constraint", "Every edge type must have one documented direction and meaning", 0.75),
        "ranking": store.add_node(pid, "assumption", "BREAK IT fragility ranking corresponds to useful attack priority", 0.2),
        "evidence": store.add_node(pid, "unknown", "Which evidence schema is sufficient for auditability?", 0.1),
        "tests": store.add_node(pid, "fact", "Core unit tests pass on the current implementation", 0.9,
                                [{"source": "python -m unittest discover -s tests -v", "observed_at": "2026-08-27"}]),
        "boundary": store.add_node(pid, "constraint", "WOS and Reality Compiler remain excluded until Core stability gates pass", 1.0),
    }
    for source, target, relation in [
        ("goal", "types", "depends_on"), ("goal", "semantics", "depends_on"),
        ("goal", "ranking", "depends_on"), ("goal", "evidence", "depends_on"),
        ("goal", "tests", "supports"), ("goal", "boundary", "depends_on")]:
        store.add_edge(pid, nodes[source]["id"], nodes[target]["id"], relation)
    return store.graph(pid)


def self_audit(store: Store) -> dict[str, Any]:
    graph = ensure_self_graph(store)
    engine = Engine(graph)
    goal = next(node for node in graph["nodes"] if node["statement"] == "OMEGA analysis is trustworthy and actionable")
    return {"graph": graph, "validation": engine.validate(), "why": engine.why(goal["id"]),
            "break_it": engine.break_it(), "prove_it": engine.prove_it(goal["id"])}
