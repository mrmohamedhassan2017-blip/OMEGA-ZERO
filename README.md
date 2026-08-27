# Impossible Machine / OMEGA

OMEGA V0.11 is a local-first reasoning core that turns a problem into an explicit graph of facts, assumptions, constraints, and unknowns. It does **not** claim autonomous truth: it exposes dependencies and produces falsifiable next steps.

Verified blind-evaluation results are persisted locally by `eval-score` and can be inspected with `eval-list`; the HTTP equivalents are `POST /evaluations` and `GET /evaluations`.

## Run

Requires Python 3.11+ and has no third-party runtime dependencies.

```powershell
python -m unittest discover -s tests -v
python -m omega.cli --db data/demo.db demo
python -m omega.cli --db data/omega-self.db self-audit
python -m omega.cli benchmark
python -m omega.cli release-check
python -m omega.cli --db data/omega-self.db stability-audit
python -m omega.api --db data/omega.db --port 8787
```

Health check: `GET http://127.0.0.1:8787/health`

## API

- `POST /problems` — `{ "title": "...", "description": "..." }`
- `POST /problems/{id}/nodes` — `{ "type": "assumption", "role": "hypothesis", "statement": "...", "confidence": 0.4, "evidence": [] }`
- `POST /problems/{id}/edges` — `{ "source_id": "...", "target_id": "...", "type": "depends_on" }`
- `GET /problems/{id}/graph`
- `GET /problems/{id}/audit` — ordered append-only mutation events
- `PATCH /problems/{id}` — update title or description
- `PATCH /nodes/{id}` — update statement, confidence, evidence, status, or role
- `DELETE /nodes/{id}` — delete a node and its incident edges
- `DELETE /edges/{id}` — delete one relationship
- `GET /problems/{id}/export` — canonical portable bundle with SHA-256 fingerprint
- `POST /imports` — validate and atomically import a bundle
- `DELETE /problems/{id}` — delete a problem and its graph
- `POST /problems/{id}/actions/why` — `{ "node_id": "..." }`
- `POST /problems/{id}/actions/break-it` — `{}`
- `POST /problems/{id}/actions/prove-it` — `{ "node_id": "..." }`
- `POST /problems/{id}/actions/what-if` — `{ "node_id": "...", "value": false }`
- `POST /problems/{id}/actions/validate` — `{}`

## Relationship semantics

- `A depends_on B`: A requires B to hold or be resolved.
- `A supports B`: A increases support for B.
- `A contradicts B`: A conflicts with B; structural impact is treated symmetrically.
- `A relates_to B`: association only; core inference ignores it.

Every operation result declares semantic `contract_version: "1.0"`. WHY follows prerequisites and incoming supporters and reports direct challenges. WHAT IF propagates to dependents, supported claims, and contradictory nodes while explicitly avoiding a causal claim. Older `supports` edges are reversed once by schema migration to match the intuitive direction.

## Self-application

`self-audit` creates an idempotent graph for the claim that OMEGA's own analysis is trustworthy and actionable, then runs validation, WHY, BREAK IT, and PROVE IT against that graph. Its database persists under `data/omega-self.db`.

Current self-audit priority: specify auditable evidence, then validate whether BREAK IT ranking matches useful real-world attack order. See [docs/SELF_AUDIT.md](docs/SELF_AUDIT.md).

Evidence records have a normalized contract: `source`, `observed_at`, `method`, `reliability`, `verification_status`, and `note`. Legacy strings remain readable but are explicitly marked `legacy`. BREAK IT exposes its score components and the calculated evidence strength.

BREAK IT uses a validated and disclosed scoring profile. The default is `balanced-v1`; sensitivity tests also run confidence-heavy, dependency-heavy, and evidence-heavy profiles against separately stored product, incident, and science fixtures.

The ontology has two axes. `type` records epistemic state (`fact`, `assumption`, `constraint`, `unknown`); `role` records function (`measurement`, `prediction`, `policy`, `question`, and related roles). Invalid type/role pairs are rejected. Older databases receive a safe default role during schema migration.

## Portability and recovery

```powershell
python -m omega.cli --db data/omega.db export PROBLEM_ID --out problem.omega.json
python -m omega.cli --db data/other.db import problem.omega.json
python -m omega.cli --db data/omega.db backup backups/omega.db
python -m omega.cli --db data/omega.db restore backups/omega.db
```

Imports verify the bundle fingerprint and the complete graph before one transaction writes anything. Exceptions roll transactions back. `release-check` verifies deterministic export, semantic round-trip, imported graph validity, atomic tamper rejection, and backup restoration.

SQLite uses WAL mode and a busy timeout. `stability-audit` launches multiple Python writer processes against one temporary database as one of its gates. See [docs/CORE_STABILITY.md](docs/CORE_STABILITY.md) for what passing currently means and what it does not mean.

Every successful mutation writes an audit event in the same database transaction. Failed transactions write neither state nor event, and no-op updates create no noise. When an older database enables auditing, OMEGA writes an explicit `audit_baseline`; it never invents historical events.

For first use, copy [launch.problem.json](C:/Users/Eng-Mohamed%20Hasan/Documents/Codex/Impossible-Machine-OMEGA/examples/launch.problem.json), edit its statements/evidence, and run `spec-check` followed by `run-spec`. The generated Markdown report is suitable for review before any external blind evaluation.

## Blind external evaluation

The evaluator must choose `expected_order` before OMEGA runs. Preparation creates a public case containing only a cryptographic commitment and a private reveal containing the labels and random salt.

```powershell
python -m omega.cli --db data/omega.db export PROBLEM_ID --out case.bundle.json
python -m omega.cli eval-prepare case.bundle.json labels.json --public-out public.json --reveal-out private-reveal.json
python -m omega.cli eval-run public.json --out prediction.json
python -m omega.cli eval-score public.json prediction.json private-reveal.json --out result.json
python -m omega.cli eval-aggregate result-1.json result-2.json
```

Do not give `private-reveal.json` to the system running `eval-run`. Modification of the case, prediction, or reveal is rejected. See [docs/EVALUATION_PROTOCOL.md](docs/EVALUATION_PROTOCOL.md).

## V0.x boundary

Included: local persistence, typed graph, dependency-cycle protection, graph validation, deterministic WHY / BREAK IT / PROVE IT / WHAT IF, HTTP API, CLI demo, self-audit, tests.

Excluded on purpose: LLM integration, UI, authentication, multi-user sync, WOS, Reality Compiler, and claims of automated proof.

See [docs/DECISIONS.md](docs/DECISIONS.md) and [CHANGELOG.md](CHANGELOG.md).
