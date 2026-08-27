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

## ADR-007 — Structured evidence contract

**Status:** Accepted — 2026-08-27

Every evidence record is normalized to source, observation time, collection method, reliability from 0 to 1, verification status, and an optional note. Verification status is one of unverified, corroborated, reproduced, disputed, retracted, legacy. Old string evidence remains readable but receives an explicit legacy status and low derived strength.

Evidence strength combines declared reliability with verification state. It is an analysis input, not a probability of truth. BREAK IT exposes the strength and all score components so its ranking can be audited.

## ADR-008 — Ranking needs executable gates and external cases

**Status:** Accepted — 2026-08-27

Keep small synthetic benchmark cases as executable invariants for confidence, evidence, dependency blast radius, and node-type policy. A perfect score on these constructed cases does not establish real-world usefulness. The ranking assumption remains in `testing` until reference problems with independently chosen attack priorities are added.
