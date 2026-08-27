# Changelog

## 0.6.0 — 2026-08-27

- Added versioned contracts for all edge types and four core operations.
- Corrected `supports` to the intuitive supporter-to-supported direction.
- Added one-time schema migration for existing support edges.
- Updated WHY to report prerequisites, supporters, unresolved gaps, and challenges.
- Updated WHAT IF propagation and PROVE IT dependency controls.
- Added a labelled end-to-end operation benchmark with five checks.
- Removed an untested invalid-role error path from BREAK IT.
- Expanded the suite from 26 to 29 tests.

## 0.5.0 — 2026-08-27

- Corrected transaction handling so exceptions roll back instead of committing partial changes.
- Added deterministic canonical problem export with SHA-256 fingerprint.
- Added validated atomic import with fresh local IDs and dependency-cycle rejection.
- Added cascading problem deletion plus SQLite backup and restore commands.
- Added HTTP export/import/delete lifecycle endpoints.
- Added five executable release gates and integrated them into self-audit.
- Expanded the suite from 20 to 26 tests.

## 0.4.0 — 2026-08-27

- Added a functional role axis while preserving the four epistemic node types.
- Added constrained type-role validation and HTTP rejection of invalid pairs.
- Added automatic schema migration for databases created before roles existed.
- Added 12 taxonomy reference cases across product, incident, and science domains.
- Integrated taxonomy evidence into OMEGA's persistent self-graph.
- Expanded the suite from 16 to 20 tests.

## 0.3.0 — 2026-08-27

- Added a normalized, validated evidence contract with legacy compatibility.
- Added derived evidence strength and transparent BREAK IT score components.
- Added an executable ranking benchmark with top-1 accuracy and mean reciprocal rank.
- Integrated benchmark results into self-audit without overstating synthetic evidence.
- Expanded the suite from 11 to 16 tests, including HTTP evidence rejection.

## 0.2.0 — 2026-08-27

- Added idempotent OMEGA self-graph and `self-audit` command.
- Added graph validation and structured evidence storage support.
- Added node updates and lifecycle statuses.
- Rejected self-references, duplicate edges, and cyclic dependencies.
- Added full HTTP flow tests and expanded the suite from 5 to 11 tests.
- Documented the first self-audit and its next falsifiable priorities.

## 0.1.0 — 2026-08-27

- Added local SQLite Problem/Assumption Graph.
- Added Fact, Assumption, Constraint, and Unknown nodes.
- Added WHY, BREAK IT, PROVE IT, and WHAT IF operations.
- Added HTTP API, CLI demo, test suite, README, and decision log.
