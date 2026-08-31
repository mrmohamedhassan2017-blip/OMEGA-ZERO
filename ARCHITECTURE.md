# OMEGA Architecture

This documents the implementation that exists at V0.21.0.

## Components and data flow

Browser workspace (`omega/web`) or CLI (`omega.cli`) → HTTP/API or direct application call → transactional store (`omega.store`) → SQLite. Analysis reads a complete graph into `omega.engine`, which returns deterministic, versioned operation results. `omega.api` serves both JSON endpoints and packaged static assets.

## Persistence and graph model

SQLite stores problems, typed nodes, directed edges, append-only audit events, schema metadata, and verified evaluation records. WAL mode, busy timeout, transactions, integrity checks, backup/restore, and atomic import protect persistence. Nodes use epistemic types `fact`, `assumption`, `constraint`, `unknown`; roles describe function. Edge semantics are `depends_on`, `supports`, `contradicts`, and `relates_to`. Dependency cycles and self-edges are rejected.

## Evidence and confidence

Claims store normalized evidence records, confidence from 0–1, status, assumptions, uncertainty, and falsification condition. Evidence contains source, method, reliability, verification status, observation time, and note. BREAK IT combines disclosed confidence, dependency, and evidence components; scores are prioritization signals, not proof.

## UI

The framework-free local workspace supports problem selection, node and edge editing, destructive confirmations, claim inspection, typed graph styling, directed relationships, zoom/pan/fit, and visual WHY/BREAK IT/PROVE IT/WHAT IF results. Raw JSON is available only through a developer disclosure.

## AI/provider abstraction

There is no LLM or provider integration in the stable Core. Analyses are deterministic. Future provider work must be an explicit adapter boundary and must not bypass evidence, permission, or audit contracts.

## Tests

`unittest` covers store/Core behavior, API and UI contracts, persistence, portability, declarative specs, evaluation protocol, concurrency, release gates, and continuity. Benchmarks cover operation semantics, taxonomy, ranking, and sensitivity.

## Extension points

Additions should enter through versioned CLI/API contracts, store migrations, and deterministic engine modules. Reality Compiler, WOS, adapters, and simulations are future layers, not current components. Historical design detail remains in `docs/ARCHITECTURE.md` and `docs/DECISIONS.md`.
