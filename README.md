# Impossible Machine / OMEGA

## Unified Command Console and Mission Engine

OMEGA now exposes a single operator surface without adding a new control plane:

- `python -m omega.cli console "ZERO, status"` routes natural operator commands to ZERO/OMEGA roles.
- `python -m omega.cli mission create "objective"` creates a durable local mission.
- `python -m omega.cli mission challenge <mission_id>` asks ZERO to identify missing evidence, conditions, and authority concerns.
- `python -m omega.cli mission execute <mission_id>` executes only when authority is sufficient.
- `python -m omega.cli mission verify <mission_id> --evidence-ref "<evidence>"` records a ZERO verdict from concrete evidence.
- `python -m omega.cli experiment-override status|enable|disable` manages the temporary internal-only constitutional experiment mode.

The same surface is available through the existing API server via `/console` and `/missions`, and the web UI includes a lightweight command console plus mission dashboard. OMEGA may propose and execute bounded internal work; ZERO owns evidence, claims, verdicts, and authority gates. The temporary experiment override is limited to A0 read, A1 internal execution, and A2 internal preparation. It does not grant external write, financial, security, account, or unknown-action authority.

## ZERO Agency Kernel precursor

`python -m omega.cli zero-cycle` runs the minimal SHADOW decision cycle. It persists a branch/action graph,
parks externally waiting branches, ranks only authorized executable actions with inspectable EVA components,
records a RED challenge and decision memory, and preserves typed evidence boundaries. `python -m omega.cli
zero-stress` runs the separate simulation-only ZEU stress baseline. ZEU is non-transferable, non-redeemable,
and has no real monetary value; it cannot populate the real Economic Ledger or Mission I value.

When the executable queue is empty, `python -m omega.cli zero-options` operates the bounded Option-Creation
Engine. It generates complete, measurable options, rejects busywork, ranks candidates using EVA/EVSI plus
execution-friction and evidence-quality factors, records RED objections, and executes only actions already
inside authority. External publication remains separately gated.

`python -m omega.cli zero-discovery` operates the independent `ZERO-DISCOVERY-001` distribution cycle. It
keeps publication, discovery, visit, intent, installation, usage, demand, willingness-to-pay, and payment
evidence separate; ranks lawful discovery surfaces; rejects fake engagement; and never changes the frozen
`ZERO-INBOUND-001` success rule.

`python -m omega.cli zero-economic-bridge` ranks machine-consumable value primitives, freezes the cheapest
independent-consumption experiment, and simulates provenance-bearing conditional ZEU contracts. Simulation,
self-purchase, and internal settlement never populate the real Economic Ledger; no real payment rail or native
asset is implemented.

`python -m omega.cli development-governor` performs one bounded, read-only ZERO evolution cycle. It ranks
the current bottleneck from repository evidence and writes a compact source-hashed checkpoint; it never runs
work, grants authority, calls a model, contacts an external service, or promotes internal activity to value.

`python -m omega.cli capability-fabric` operates one bounded Capability Fabric cycle. It discovers only
repository/host capabilities that are actually observable, builds deterministic TaskCapabilityProfiles, and
produces provider-agnostic route recommendations with explicit alternatives, fallbacks, authority, and
verification plans. The router is SHADOW-only: it does not invoke models, execute commands, contact the
network, grant authority, or replace the existing Supervisor, Wake Plane, AgentBackend, or Host Verification.
Unknown and unavailable capabilities remain parked rather than being silently downgraded. Registry, replay,
performance-memory, and cycle records are persisted under `.omega/zero/`.

`python -m omega.cli value-cycle` runs one bounded Real-World Value Engine cycle. It recovers prior killed and
parked hypotheses, compiles provenance-linked problem evidence, ranks candidates transparently, freezes the
cheapest baseline-first experiment, and stops at authority boundaries. The read-only commands `value-status`,
`value-opportunities`, `value-experiments`, and `value-evidence` inspect the persisted result. L0-L7 levels are
not interchangeable: owner, bot, synthetic, duplicate, unverifiable, and prompt-injected events cannot become
external evidence; WTP is not settlement; and no revenue or value is inferred from internal activity.

`python -m omega.cli value-frontier-cycle` runs the bounded ZRWVE V1.1 adjacent-domain search and multi-baseline
falsification. It excludes semantic duplicates of killed wedges, caps the serious frontier at 12 candidates,
compares configuration/rules/transactions/idempotency/monitoring/existing platforms/human review before ZERO,
and accepts `NO_UNDEFEATED_OPPORTUNITY_FOUND` as a valid result. `value-frontier-status` is read-only. The latest
cycle found no decision, verified attention, or reliability advantage and therefore remains parked at L0/0 KWD.

`python -m omega.cli value-deep-cycle` runs the mandatory ZRWVE V1.2D twelve-pass investigation over the frozen
T1/T2/T3 targets (GitOps revision continuity, dataflow resume, and backup/restore truth). It compiles a
provenance-linked corpus, operator traces, B0–B3 baselines, adversarial and counterfactual ledgers, attention
burden, negative evidence, saturation, and a blinded incident packet. The cycle is fail-closed: it performs no
network access, model call, Supervisor execution, or external write. `value-deep-status` is read-only. Current
internal evidence leaves the result at `EXTERNAL_INCIDENT_VALIDATION_REQUIRED` with 15 qualifying public
incidents; no baseline break or attention gap is promoted without independent sanitized T2 evidence.

`python -m omega.cli value-deep-packet-audit` runs the local-only ZRWVE V1.2E hardening gate on that T2
boundary. It freezes the required E1 real sanitized incident, E2 actual B3 configuration, E3 ordered operator
judgment trace, and E4 external verification criterion; preserves causal/provenance and decision-time versus
outcome separation; and validates blind `B3_WINS`, `ZERO_WINS`, `PARITY`, and `INCONCLUSIVE` outcomes. Test-only
fixtures, duplicate/synthetic/owner/bot/opinion/secret/incomplete packets, and weak verification claims fail
closed. The resulting packet is `READY_FOR_OWNER_AUTHORIZATION` with authority closed and no external write,
contact, model, network, Supervisor, or Wake Plane action.

`python -m omega.cli value-deep-binding-audit` performs the follow-on ZRWVE V1.2F channel and participant
binding audit without sending. It records configured transport capabilities separately from authority, keeps
the E2-01 Gmail grant isolated, ranks only public T2 incident records, and freezes the participant/message/
packet hashes, expiry, dedupe, privacy, and ZRWVE-only thread policy. A public incident is not a qualified
participant unless an attributable independent actor and a legitimate one-to-one route are verified. The
current result is `READY_TO_BIND_BUT_NO_QUALIFIED_PARTICIPANT`; six candidates were rejected, zero messages
were sent, and the external-action envelope remains closed. Artifacts and host-gate evidence are stored under
`.omega/zero/`; V0.30, L0, 0 KWD, and all E2-01 boundaries remain unchanged.

`python -m omega.cli value-deep-participant-discovery` performs the V1.2G discovery-only continuation. It
reviews up to 15 serious T2 records, resolves only first-party public identities, and keeps qualification
separate from contactability. The current corpus produced six `QUALIFIED_BUT_NOT_CONTACTABLE` dossiers and no
`QUALIFIED_AND_CONTACTABLE` participant: a public GitHub profile is identity/evidence only, not a one-to-one
contact route. The cycle is idempotent, saturated for the current corpus, performs no network or external write,
and parks at `PARK_UNTIL_NEW_PUBLIC_EVIDENCE` while preserving the V1.2F packet/message/participant hashes.

ZRWVE V1.2H adds a design-only passive real-incident intake path without publishing it. Six candidate surfaces
were scored against voluntary participation, provenance, E1/E2/E3/E4 completeness, privacy, sanitization,
spam resistance, deduplication, auditability, Wake Plane compatibility, attention cost, complexity, write cost,
and maintenance. One GitHub Issue Form was selected for a two-stage flow: required Stage 1 qualification followed
by an optional sanitized Stage 2 incident packet. Trusted source observation supplies provenance; participant text
cannot self-assert independence. Opinion, anonymous/owner/bot/OMEGA submissions, duplicates, secrets, spam, and
prompt injection fail closed. Complete packets reuse the frozen blind B3-versus-minimal-ZERO contract. The exact
one-file publication packet was subsequently authorized and published to the separate public repository at commit
`bac95d4eafe3180638d90694539e902aa375b723`. Its content hash matches the frozen contract. The existing read-only
GitHub adapter now routes only qualified Stage 1 or complete Stage 2 records through a distinct fail-closed Wake
Plane source; it never stores raw issue bodies and never treats the form as a ZERO-INBOUND install event. Publication
is not independent discovery, incident evidence, demand, or value. Existing independent discovery remains `NOT_PROVEN`.

Artifacts live under `.omega/zero/`. `NEXT_TASK.md` compatibility and all existing Supervisor, Gmail, AVF,
and V0.30 workflows remain unchanged.

The Wake Plane is a separate, non-authoritative trigger layer. `wake-plane-run --mode SHADOW` observes
without waking; `PASSIVE_PRODUCTION_VALIDATE_ONLY` validates routing without waking; and
`PASSIVE_PRODUCTION` may request the existing Supervisor start path only for a real, provenance-validated,
deduplicated event. The installed Windows task uses the canonical repository and Python interpreter. GitHub
inbound detection is read-only for the designated public publication repository; owner/bot activity, metrics,
and synthetic events are never independent evidence. V0.30 still requires two independently attributable
evaluator identities, and the real evaluator count remains zero.

## Gmail market channel (E2-01)

OMEGA's Gmail adapter uses a Google **Desktop app** OAuth client, a loopback callback, and only
`gmail.send` plus `gmail.readonly`. The latter is required to ingest replies; the adapter does not
request mailbox modification or deletion. Put the downloaded Desktop OAuth client JSON at:

`%LOCALAPPDATA%\OMEGA\gmail\oauth-client.json`

Then inspect the channel with `python -m omega.cli gmail-channel status`. The one-time
`python -m omega.cli gmail-channel consent` flow opens Google's consent screen and verifies that
the authorized mailbox is exactly `omega.agent.runtime@gmail.com`. Tokens are encrypted with
Windows DPAPI at `%LOCALAPPDATA%\OMEGA\gmail\token.dpapi`; neither file belongs in the repository.
Readiness verification reads only the Gmail profile and never sends outreach. E2 remains bounded
by the frozen message, 10-contact maximum, zero financial authority, and immediate kill switch.

OMEGA also includes a local Capability Discovery Engine. Run `python -m omega.cli capability-discover` to analyze recorded incidents, score candidate capabilities, freeze and evaluate the next experiment, and update machine-readable self-model/evidence artifacts. Internal RED and acceptance evaluations are explicitly separate from external human evidence.

The Autonomous Venture Foundry runs with `python -m omega.cli venture-foundry`. Its first selected venture is a privacy-bounded agent-runtime audit MVP. Run `python -m omega.cli venture-audit-log <events.jsonl> --json-out report.json --html-out report.html`. AVF is in simulation/recommendation mode: it cannot transfer funds or claim revenue without verified provenance.

Run `python -m omega.cli venture-e2` to regenerate the product positioning, segment ranking, competitive gap, trust package, frozen demand experiments, external-action queue, Capability Investment Fund, and Capability Frontier. This prepares E2 but never claims that E2 occurred.

Run `python -m omega.cli founder-os` to regenerate the Uncertainty Ledger, Assumption Graph, stakeholder roles, demand-strength model, External Identity/Broker state, Board Review, and the single bounded authorization Decision Case. It never executes an external adapter merely because credentials exist.

Run `python -m omega.cli market-barrier` to materialize the bounded market-contact policy, frozen controller state, response intelligence schema, authorization case, and disabled multi-rail Treasury specification.

OMEGA V0.21 Usability Hardening is a local-first reasoning application that turns a problem into an explicit graph of facts, assumptions, constraints, and unknowns. It does **not** claim autonomous truth: it exposes dependencies and produces falsifiable next steps.

## Current verification (2026-08-29)

The current full-suite verification passes all 441 unit, integration, smoke, and continuity tests after the V1.2H
publication and read-only Wake routing integration, with ResourceWarning promoted to an error. The targeted intake/Wake
set passed 38/38 and the broader relevant regression set passed 69/69. The ranking/taxonomy/operations/sensitivity benchmarks, all five portability and recovery release gates, and all 11 internal stability gates
(including multi-process writes) also pass. This establishes an internally verified Core Alpha, not V1 readiness:
independently collected user-outcome evidence and externally supplied blind-evaluation records are still required.

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
python -m omega.cli development-governor
python -m omega.api --db data/omega.db --port 8787
```

Open `http://127.0.0.1:8787/` for the V0.21 workspace. The same server exposes the API; health check: `GET http://127.0.0.1:8787/health`.

## Continue work safely

The repository is the source of truth. A new developer or AI session starts with [PROJECT_STATE.md](PROJECT_STATE.md), then runs:

```powershell
python -m omega.cli project-status --verify-tests
python -m omega.cli continue
```

The first command validates path, version metadata, continuity files, the NEXT_TASK baseline, Git state, and the real test suite. The second produces a concise execution context without reading environment variables or credentials. See [RUNBOOK.md](RUNBOOK.md).

The workspace supports safe node and relationship editing, explicit destructive confirmations, a selectable graph with inspector, typed colors, relationship arrows, zoom/pan/fit controls, and visual WHY / BREAK IT / PROVE IT / WHAT IF results. Raw JSON remains available under the developer disclosure.

The workspace creates and reopens persisted problems, renders typed nodes and relationships, lets the user select a node, records evidence/confidence/assumptions/uncertainty/falsifier fields, and runs WHY, BREAK IT, PROVE IT, and WHAT IF against the stored graph.

## API

- `POST /problems` — `{ "title": "...", "description": "..." }`
- `POST /problems/{id}/nodes` — `{ "type": "assumption", "role": "hypothesis", "statement": "...", "confidence": 0.4, "evidence": [], "assumptions": [], "uncertainty": "...", "falsifier": "..." }`
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

## ZERO value-bridge boundary

`python -m omega.cli zero-value-bridge` freezes the smallest CI-consumption experiment without performing an external action. It records the exact reliability-verification unit, L0-L6 evidence ladder, independent provenance requirements, RED attacks, ranked acquisition routes, and the minimum pinned-commit consumer interface under `.omega/zero/`. ZEU remains simulation-only; this workflow cannot create revenue, settlement, demand, or a real token claim.

## ZERO Cybersecurity Expert Console

`python -m omega.cli cyber status`, `python -m omega.cli cyber train`, and `python -m omega.cli cyber ask "..."` expose a defensive/research cybersecurity capability layer. It classifies scope before action and fails closed for unsafe or unauthorized requests. The current state is `NOT_READY_RESEARCH_CURRICULUM_IN_PROGRESS`; it does not claim certified, licensed, PhD-level, or external expert status.

`python -m omega.cli cyber mastery` runs the current safe practical-mastery campaign: 20 deterministic domain labs, unseen-case assessment, and final-exam freezing. Passing this campaign supports internal practical evidence only; ZERO still refuses external/expert promotion until stronger research-grade evidence exists.

`python -m omega.cli cyber research-eval` runs the frozen research-grade promotion mission: 40 novel/adversarial cases across all 20 domains, expert-vs-baseline comparison, replication, stability, and critical-failure checks. `python -m omega.cli cyber promotion-status` reports the current promotion verdict. Passing internal research evidence still does not create public/expert status without independent external evidence.

`python -m omega.cli cyber external-eval-freeze` creates the Cyber Expert Independent External Evaluation Packet V1. The packet freezes blind challenges, scoring, provenance rules, and anti-fabrication gates. `python -m omega.cli cyber external-eval-status` reports whether two independent evaluator submissions have been accepted. Owner/self/internal submissions do not count as independent evidence.

## OMEGA / ZERO Public Gateway

`python -m omega.cli public-gateway init` and `python -m omega.cli public-gateway scan fixture:known-good|fixture:known-bad` expose the local fixture-backed gateway for `CODE_SCAN`. This is not a public deployment. Public release remains blocked until a separate deployment/public-boundary review passes.

`python -m omega.cli public-gateway readiness` checks local release readiness: public/private/secret component classification, API exposure, SSRF/path traversal/command injection probes, frontend secret/privileged-control inspection, and local deployment architecture. `PUSH_READY` is not publication authority; explicit release authorization is still required.

`python -m omega.cli public-gateway mission-run` executes the local Public Gateway V1 roadmap from PG-00 through PG-12. It records mission state under `.omega/public-gateway/`, runs known-good/known-bad/invalid-request benchmark evidence, verifies the local public experience, and ends at push-ready or blocked without publishing.

`python -m omega.cli zero-counterparty` operates the minimum problem-first counterparty and Work Order cycle. It records a bounded public-problem set, rejects weak capability matches, validates non-skippable Work Order stages, applies RED review, and freezes at proposed-only whenever independent acceptance or external authority is absent. Public issues are evidence of problems, never automatic demand.

`python -m omega.cli preb-simulate` records provider resilience state without invoking a provider. Codex quota exhaustion is a temporary resource wait for the affected branch; deterministic Host execution continues, and checkpoint recovery uses one bounded availability probe. No quota is bypassed and no alternate AI provider is assumed.

`python -m omega.cli zero-truth-cycle` operates the Reality Ledger, Hypothesis Registry, and Bottleneck Intelligence cycle. It ingests references and hashes rather than private payloads, keeps evidence levels separate, identifies the dominant missing proof edge, and rejects internal activity that does not improve a meaningful decision.

`python -m omega.cli zmi-cycle` tests whether independent systems can discover and consume the existing pinned CI capability without OMEGA contact. It records child bottlenecks and a capability contract but does not create a new platform or synthetic traffic.

`python -m omega.cli zopd-cycle` runs the post-wedge open-problem discovery funnel. It records public problem evidence, incumbent baselines, authority/data boundaries, narrow value primitives, aggressive rejections, top-three falsification experiments, and an explicit no-winner result when differentiation is not demonstrated.

`python -m omega.cli zmc-convergence-cycle` converges the open-problem evidence on H-VEH-001. It records five baseline-challenged economic-option classes and exactly one bounded master project, while refusing to turn detection, provenance, synthetic fixtures, or unexecuted options into economic value.

`python -m omega.cli veh-qualification-cycle` performs metadata-minimal qualification of already-evidenced owner capabilities. It can return `NO_OPTION` without reading secrets or fabricating a charge, entitlement, deadline, authority, or value event.

`python -m omega.cli zad-cycle` mines killed wedges for a demonstrated comparative advantage. It compares persistence, adaptive reranking, portfolios, cross-system reasoning, attention economics, capability acquisition, and learning against strong ordinary baselines and can explicitly return no demonstrated advantage.

`python -m omega.cli zdoa-benchmark` runs the frozen 90-run Dynamic Opportunity Arena. It compares ZERO with a dynamic rules engine plus batched human review under information, resource, and authority parity, applies an explicit complexity tax, and never promotes simulated advantage into external utility or economic value.
