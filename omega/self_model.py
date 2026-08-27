from __future__ import annotations

from typing import Any

from .engine import Engine
from .store import Store
from .benchmark import run_all_benchmarks
from .release import run_release_gates

TITLE = "OMEGA Core can produce trustworthy, actionable analysis"


def ensure_self_graph(store: Store) -> dict[str, Any]:
    existing = store.find_problem(TITLE)
    if existing:
        graph = store.graph(existing["id"])
        by_statement = {node["statement"]: node for node in graph["nodes"]}
        external_statement = "Do independent evaluators agree that OMEGA priorities are useful?"
        if external_statement not in by_statement:
            external = store.add_node(existing["id"], "unknown", external_statement, 0.1, role="question")
            goal_node = by_statement.get("OMEGA analysis is trustworthy and actionable")
            if goal_node:
                store.add_edge(existing["id"], goal_node["id"], external["id"], "depends_on")
            graph = store.graph(existing["id"])
            by_statement = {node["statement"]: node for node in graph["nodes"]}
        evidence_question = by_statement.get("Which evidence schema is sufficient for auditability?")
        if evidence_question:
            store.update_node(evidence_question["id"], confidence=0.75, status="testing", evidence=[{
                "source": "audit_events + evaluations schema and lifecycle tests", "observed_at": "2026-08-27",
                "method": "append-only-atomic-mutation-and-evidence-fingerprint-audit", "reliability": 0.88,
                "verification_status": "reproduced", "note": "Audit begins at enablement; external provenance sufficiency remains unproven."}])
        ranking = by_statement.get("BREAK IT fragility ranking corresponds to useful attack priority")
        if ranking:
            store.update_node(ranking["id"], confidence=0.65, status="testing", evidence=[{
                "source": "omega/fixtures/ranking_cases.json + omega.sensitivity", "observed_at": "2026-08-27",
                "method": "three-labelled-domains-across-four-scoring-profiles", "reliability": 0.7,
                "verification_status": "reproduced", "note": "Robust in internal fixtures; no external labels yet."}])
        type_claim = by_statement.get("Four node types capture the distinctions needed by real problems")
        if type_claim:
            store.update_node(type_claim["id"], confidence=0.6, status="testing", role="unverified_claim", evidence=[{
                "source": "omega.ontology:run_taxonomy_benchmark", "observed_at": "2026-08-27",
                "method": "12-human-labelled-cases-across-three-domains", "reliability": 0.65,
                "verification_status": "reproduced", "note": "Supports two-axis representability in the fixture set only."}])
        trust_claim = by_statement.get("OMEGA analysis is trustworthy and actionable")
        if trust_claim:
            store.update_node(trust_claim["id"], confidence=0.7, status="testing", role="unverified_claim", evidence=[{
                "source": "omega.release:run_release_gates", "observed_at": "2026-08-27",
                "method": "five-automated-portability-and-recovery-gates", "reliability": 0.8,
                "verification_status": "reproduced", "note": "Establishes core lifecycle behavior, not outcome usefulness."}])
        semantics = by_statement.get("Every edge type must have one documented direction and meaning")
        if semantics:
            store.update_node(semantics["id"], confidence=0.9, status="supported", role="invariant", evidence=[{
                "source": "omega.contracts + omega.operation_benchmark", "observed_at": "2026-08-27",
                "method": "versioned-contract-and-five-executable-checks", "reliability": 0.85,
                "verification_status": "reproduced", "note": "Establishes implemented semantics, not external usefulness."}])
        return store.graph(existing["id"])

    problem = store.create_problem(TITLE, "OMEGA V0.x applies its own reasoning model to its design and claims.")
    pid = problem["id"]
    nodes = {
        "goal": store.add_node(pid, "assumption", "OMEGA analysis is trustworthy and actionable", 0.25),
        "types": store.add_node(pid, "assumption", "Four node types capture the distinctions needed by real problems", 0.35),
        "semantics": store.add_node(pid, "constraint", "Every edge type must have one documented direction and meaning", 0.75),
        "ranking": store.add_node(pid, "assumption", "BREAK IT fragility ranking corresponds to useful attack priority", 0.2),
        "evidence": store.add_node(pid, "unknown", "Which evidence schema is sufficient for auditability?", 0.75, [{
            "source": "audit_events + evaluations schema and lifecycle tests", "observed_at": "2026-08-27",
            "method": "append-only-atomic-mutation-and-evidence-fingerprint-audit", "reliability": 0.88, "verification_status": "reproduced",
            "note": "Audit begins at enablement; external provenance sufficiency remains unproven."}]),
        "tests": store.add_node(pid, "fact", "Core unit tests pass on the current implementation", 0.9,
                                [{"source": "python -m unittest discover -s tests -v", "observed_at": "2026-08-27"}]),
        "boundary": store.add_node(pid, "constraint", "WOS and Reality Compiler remain excluded until Core stability gates pass", 1.0),
        "external": store.add_node(pid, "unknown", "Do independent evaluators agree that OMEGA priorities are useful?", 0.1,
                                   role="question"),
    }
    for source, target, relation in [
        ("goal", "types", "depends_on"), ("goal", "semantics", "depends_on"),
        ("goal", "ranking", "depends_on"), ("goal", "evidence", "depends_on"),
        ("tests", "goal", "supports"), ("goal", "boundary", "depends_on"),
        ("goal", "external", "depends_on")]:
        store.add_edge(pid, nodes[source]["id"], nodes[target]["id"], relation)
    store.update_node(nodes["evidence"]["id"], status="testing")
    store.update_node(nodes["ranking"]["id"], confidence=0.65, status="testing", evidence=[{
        "source": "omega/fixtures/ranking_cases.json + omega.sensitivity", "observed_at": "2026-08-27",
        "method": "three-labelled-domains-across-four-scoring-profiles", "reliability": 0.7,
        "verification_status": "reproduced", "note": "Robust in internal fixtures; no external labels yet."}])
    store.update_node(nodes["types"]["id"], confidence=0.6, status="testing", role="unverified_claim", evidence=[{
        "source": "omega.ontology:run_taxonomy_benchmark", "observed_at": "2026-08-27",
        "method": "12-human-labelled-cases-across-three-domains", "reliability": 0.65,
        "verification_status": "reproduced", "note": "Supports two-axis representability in the fixture set only."}])
    store.update_node(nodes["goal"]["id"], confidence=0.7, status="testing", role="unverified_claim", evidence=[{
        "source": "omega.release:run_release_gates", "observed_at": "2026-08-27",
        "method": "five-automated-portability-and-recovery-gates", "reliability": 0.8,
        "verification_status": "reproduced", "note": "Establishes core lifecycle behavior, not outcome usefulness."}])
    store.update_node(nodes["semantics"]["id"], confidence=0.9, status="supported", role="invariant", evidence=[{
        "source": "omega.contracts + omega.operation_benchmark", "observed_at": "2026-08-27",
        "method": "versioned-contract-and-five-executable-checks", "reliability": 0.85,
        "verification_status": "reproduced", "note": "Establishes implemented semantics, not external usefulness."}])
    return store.graph(pid)


def self_audit(store: Store) -> dict[str, Any]:
    graph = ensure_self_graph(store)
    engine = Engine(graph)
    goal = next(node for node in graph["nodes"] if node["statement"] == "OMEGA analysis is trustworthy and actionable")
    return {"graph": graph, "validation": engine.validate(), "why": engine.why(goal["id"]),
            "break_it": engine.break_it(), "prove_it": engine.prove_it(goal["id"]),
            "benchmarks": run_all_benchmarks(), "release_gates": run_release_gates()}
