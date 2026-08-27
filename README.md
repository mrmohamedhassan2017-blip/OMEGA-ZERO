# Impossible Machine / OMEGA

OMEGA V0.4 is a local-first reasoning core that turns a problem into an explicit graph of facts, assumptions, constraints, and unknowns. It does **not** claim autonomous truth: it exposes dependencies and produces falsifiable next steps.

## Run

Requires Python 3.11+ and has no third-party runtime dependencies.

```powershell
python -m unittest discover -s tests -v
python -m omega.cli --db data/demo.db demo
python -m omega.cli --db data/omega-self.db self-audit
python -m omega.cli benchmark
python -m omega.api --db data/omega.db --port 8787
```

Health check: `GET http://127.0.0.1:8787/health`

## API

- `POST /problems` — `{ "title": "...", "description": "..." }`
- `POST /problems/{id}/nodes` — `{ "type": "assumption", "role": "hypothesis", "statement": "...", "confidence": 0.4, "evidence": [] }`
- `POST /problems/{id}/edges` — `{ "source_id": "...", "target_id": "...", "type": "depends_on" }`
- `GET /problems/{id}/graph`
- `POST /problems/{id}/actions/why` — `{ "node_id": "..." }`
- `POST /problems/{id}/actions/break-it` — `{}`
- `POST /problems/{id}/actions/prove-it` — `{ "node_id": "..." }`
- `POST /problems/{id}/actions/what-if` — `{ "node_id": "...", "value": false }`
- `POST /problems/{id}/actions/validate` — `{}`
- `PATCH /nodes/{id}` — update `statement`, `confidence`, `evidence`, or `status`

Edge direction is semantic: `A depends_on B` is stored as source `A`, target `B`.

## Self-application

`self-audit` creates an idempotent graph for the claim that OMEGA's own analysis is trustworthy and actionable, then runs validation, WHY, BREAK IT, and PROVE IT against that graph. Its database persists under `data/omega-self.db`.

Current self-audit priority: specify auditable evidence, then validate whether BREAK IT ranking matches useful real-world attack order. See [docs/SELF_AUDIT.md](docs/SELF_AUDIT.md).

Evidence records have a normalized contract: `source`, `observed_at`, `method`, `reliability`, `verification_status`, and `note`. Legacy strings remain readable but are explicitly marked `legacy`. BREAK IT exposes its score components and the calculated evidence strength.

The ontology has two axes. `type` records epistemic state (`fact`, `assumption`, `constraint`, `unknown`); `role` records function (`measurement`, `prediction`, `policy`, `question`, and related roles). Invalid type/role pairs are rejected. Older databases receive a safe default role during schema migration.

## V0.x boundary

Included: local persistence, typed graph, dependency-cycle protection, graph validation, deterministic WHY / BREAK IT / PROVE IT / WHAT IF, HTTP API, CLI demo, self-audit, tests.

Excluded on purpose: LLM integration, UI, authentication, multi-user sync, WOS, Reality Compiler, and claims of automated proof.

See [docs/DECISIONS.md](docs/DECISIONS.md) and [CHANGELOG.md](CHANGELOG.md).
