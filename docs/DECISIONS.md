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

## ADR-009 — Two-axis ontology

**Status:** Accepted — 2026-08-27

Keep the four core node types as epistemic categories: fact, assumption, constraint, and unknown. Add a constrained functional `role` axis instead of multiplying top-level types. For example, a fact may be a measurement or event; an assumption may be a hypothesis or prediction; a constraint may be a policy or invariant; an unknown may be a question or missing data.

This model covers the current product, incident, and scientific reference cases while keeping graph operations dependent on epistemic state. It does not claim universal domain coverage. Unsupported type/role pairs are rejected, and schema migration assigns an explicit default role to older nodes.

## ADR-010 — Portable canonical problem bundles

**Status:** Accepted — 2026-08-27

Export a problem as canonical JSON containing semantic problem, node, evidence, and edge fields, excluding database timestamps and local IDs. Attach a SHA-256 fingerprint of the canonical payload. Import verifies the fingerprint, validates every node and edge, rejects dependency cycles, and writes the graph in one transaction with fresh local IDs.

The fingerprint detects accidental or unacknowledged modification; it is not a signature and does not establish authorship.

## ADR-011 — Roll back failed transactions

**Status:** Accepted — 2026-08-27

Database contexts commit only after successful completion. Any exception triggers rollback before closing the connection. This is a required invariant for imports and other future multi-write operations.

## ADR-012 — Release gates are executable

**Status:** Accepted — 2026-08-27

The core release check must demonstrate deterministic export, semantic export/import round-trip, graph validity after import, atomic rejection of tampering, and SQLite backup restoration. These establish lifecycle integrity, not the usefulness of recommendations to a human.

## ADR-013 — Intuitive, versioned relationship semantics

**Status:** Accepted — 2026-08-27

Relationship contract 1.0 defines `A depends_on B` as A requiring B, and `A supports B` as A providing support to B. `contradicts` is directed for provenance but symmetric for structural impact. `relates_to` carries no inference.

The earlier implementation stored supports in the opposite direction. Schema migration 4 reverses existing support edges once. Core operation responses declare their contract version so consumers can detect future semantic changes.

## ADR-014 — Operation benchmark boundary

**Status:** Accepted — 2026-08-27

Maintain a labelled end-to-end graph that checks WHY prerequisites/support/challenges, BREAK IT bottleneck selection, PROVE IT falsifiability and controls, WHAT IF propagation, and contract-version disclosure. Passing this benchmark proves conformance to the documented contract, not superiority of the contract on real decisions.

## ADR-015 — Disclosed scoring profiles and sensitivity gate

**Status:** Accepted — 2026-08-27

Move BREAK IT weights into an immutable validated scoring profile and return the active profile with every result. Test the expected top priority on separately stored product, incident, and science graphs under balanced, confidence-heavy, dependency-heavy, and evidence-heavy profiles.

Robustness across these profiles reduces weight sensitivity risk but does not replace independently authored labels.

## ADR-016 — Core-candidate and V1 are different claims

**Status:** Accepted — 2026-08-27

`stability-audit` may declare an internal Core candidate only when every executable stability gate passes. It must keep `ready_for_v1` false while external outcome evidence or independent ranking labels are missing. This prevents self-authored tests from certifying the system's real-world usefulness.

## ADR-017 — Local concurrent-write policy

**Status:** Accepted — 2026-08-27

Use SQLite WAL mode and a 10-second busy timeout. The stability gate runs four independent Python writer processes and verifies exact problem/node counts plus database integrity. This supports local concurrent writers; it is not a distributed database guarantee.
