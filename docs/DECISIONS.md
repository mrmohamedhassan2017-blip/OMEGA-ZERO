# Architecture Decision Log

## ADR-001 — Local-first SQLite core

**Status:** Accepted — 2026-08-27

Use Python standard library plus SQLite. This makes V0.1 reproducible, inspectable, and runnable without network access or credentials.

## ADR-002 — Explicit typed graph

**Status:** Accepted — 2026-08-27

Represent reasoning as problems, nodes, and directed typed edges. Node types are Fact, Assumption, Constraint, and Unknown. The graph is the source of truth; analysis outputs are derived.

## ADR-003 — Deterministic operations before AI generation

**Status:** Accepted — 2026-08-27

WHY traces supporting/dependency chains. BREAK IT ranks fragile nodes. PROVE IT generates a test protocol. WHAT IF propagates structural impact. Results are explainable and testable.

## ADR-004 — Hold the boundary

**Status:** Accepted — 2026-08-27

Do not add WOS or Reality Compiler work until the graph model, persistence, operation semantics, and API have real usage evidence and stable tests.

## ADR-005 — Dependency graph must be acyclic

**Status:** Accepted — 2026-08-27

Reject self-edges and any new `depends_on` edge that would create a directed cycle. Cycles make WHY depth and downstream impact ambiguous. Other relation types may form cycles because they do not express prerequisite ordering.

## ADR-006 — OMEGA is a subject of OMEGA

**Status:** Accepted — 2026-08-27

Maintain a persistent, idempotently seeded self-graph and run the core operations against it. Self-analysis does not prove correctness; it exposes the next falsifiable design risk and keeps architectural claims inside the same audit model as user problems.
