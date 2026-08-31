# Changelog

## Unreleased — Unified Command Console + Mission Engine + temporary internal experiment override (2026-08-31)

- Added `omega.mission_control` as a repository-local mission/command/verdict layer over the existing OMEGA stack. It stores command records, missions, claims, evidence refs, and ZERO verdicts under `.omega/missions/`.
- Added `omega.experiment_override` for `ZERO_CONSTITUTIONAL_EXPERIMENT_MODE`, limited to A0 read, A1 internal execution, and A2 internal preparation. External writes, financial actions, security testing, account mutation, and unknown actions fail closed.
- Extended the existing CLI with `console`, `mission`, and `experiment-override` commands.
- Extended the existing API with `/console` and `/missions` routes and added a lightweight web command console/mission dashboard.
- Added a narrow Supervisor overlay that can clear an `AUTH_REQUIRED` blocker only for the same durable task when the temporary internal experiment authority explicitly allows the internal action. No provider route, Wake Plane, production default, external authority, or financial authority was changed.
- Verified and closed the temporary experiment override after a bounded internal mission reached `ZERO_VERIFIED`.
- Verification: syntax PASS; targeted tests 56/56 PASS; full suite 560/560 PASS with ResourceWarning-as-error; benchmark PASS; release gates 5/5 PASS; stability gates 11/11 PASS; diff check PASS; non-test secret scan PASS.

## Unreleased — Supervisor start CLI binding repair (2026-08-30)

- Fixed `python -m omega.cli supervisor start` by aliasing the Wake Plane callback import so it no longer shadows the Supervisor `start_scheduled_task` binding inside `main()`.
- Verified the command now dispatches the Windows Scheduled Task. The runtime still exits fail-closed to the existing `HARD_BLOCKER` when no material wake/authority boundary exists, so `AUTONOMY: ACTIVE` is not claimed.
- Verification completed with py_compile PASS, Supervisor regression 18/18 PASS, full suite 547/547 PASS with ResourceWarning-as-error, release gates 5/5 PASS, and stability audit exit 0.

## Unreleased — Economic Platform Registry + Multi-Backend Shadow Benchmark (2026-08-30)

- Added a conservative `EconomicPlatformRegistry` to the existing Economic Engine. It covers all 27 required candidate platforms, preserves platform policy freshness/evidence refs, classifies unknown facts fail-closed, and keeps execution-ready/payout-ready counts at zero absent explicit authority and verified eligibility.
- Added `economic-platform-registry` CLI output and persisted the current registry under `.omega/zero/economic/platform_registry.json`. The selected first truth experiment is passive GitHub inbound observation only; no external write, financial action, security action, or evidence promotion occurred.
- Added a `multi-backend-shadow-benchmark` controller that freezes 12 task classes, records prompt/baseline hashes, imports only existing real provider evidence, rejects missing/fallback/mock/cached trials, and recommends `KEEP_SHADOW` when comparative evidence is insufficient.
- Current benchmark campaign `multi-backend-shadow-4de440af507c` records 3 valid Claude trials from prior verified shadow evidence and 0 valid Codex trials because Codex remains `WAITING_RESOURCE`. Cost/token metrics remain `UNKNOWN`, not zero. Production routing and default provider remain unchanged.
- Verification completed with syntax PASS, targeted tests 21/21 PASS, full suite 539/539 PASS with ResourceWarning-as-error, benchmark PASS, release gates 5/5 PASS, stability audit PASS, git diff --check PASS, and non-test secret scan showing no credential values.

## Unreleased — Claude OmniRoute nonce canary (2026-08-30)

- Added `omega.claude_omniroute_canary` and `claude-omniroute-canary` to perform exactly one fresh nonce-bound, read-only provider canary through the existing Capability Fabric, Task Continuity, OmniRoute transport marker, and Claude backend.
- Added provider-canary-only Capability Fabric routing support via `required_capability_id` without promoting Claude to a general active/default route. Presence alone remains insufficient for normal routing eligibility.
- Added `PROVIDER_CANARY` to the bounded Claude task classes; its prompt is sent exactly for nonce verification and Host Verification compares the extracted provider response without normalizing internal content.
- Added regressions for exact nonce matching, wrong-backend false positives, stale/wrong nonce rejection, and provider-canary routing without general promotion. First live attempt failed closed on Codex route selection; second live attempt verified Claude via OmniRoute with no repository source changes, external writes, financial actions, or security actions.

## Unreleased — ZERO Autonomous Economic Engine V2.0 (2026-08-30)

- Added `omega.economic_engine` as a machine-enforceable economic policy layer inside the existing ZERO/OMEGA architecture. It defines typed mission, opportunity, claim, event, ledger, authority, approval, evidence, cash-flow, scale, and causal-memory models without creating another Supervisor, Wake Plane, continuity system, authority system, or runtime.
- Implemented exact L0-L7 reality ladder checks, A0-A6 authority classes, approval expiry/revocation checks, stale-evidence rejection, proposal/demand and owner/independent evidence separation, cash/profit/liquidity/unrealized-value separation, hash-chain ledger verification, duplicate economic side-effect idempotency protection, security-scope blocking, and scale gates for negative unit economics, liquidity, concentration, and authority risk.
- Added read-only/inspection CLI commands: `economic-status`, `economic-opportunities`, `economic-ledger`, `economic-claims`, `economic-evidence`, `economic-engines`, `economic-verify`, and `economic-bootstrap-audit`. Bootstrap writes only `.omega/zero/economic/*` evidence from repository truth and records 0 USD verified economic value, 0 external writes, 0 financial actions, and 0 security actions.
- Added `tests/test_economic_engine.py` with 14 focused regressions covering ladder promotion, demand misclassification, contract/payment/profit separation, stale evidence, expired/revoked approval, authority levels, FX freshness, duplicate side effects, ledger integrity, contradictions, scale gates, security scope, utility estimates, bootstrap persistence, and status/verification JSON.

## Unreleased — ZERO park-time probability/statistics campaign (2026-08-30)

- Added campaign `probability-statistics-001` as a bounded consumer of the existing scientific-learning and Task Continuity engines; no scheduler, Supervisor, Wake Plane, or production route was added.
- Completed 14/14 ordered units with official/peer-reviewed source provenance, active recall, novel-problem transfer, limitations, error analysis, and explicit knowledge states. Seven units are `PROBLEM_TESTED`, seven are `APPLIED`, and zero are `TRUSTED`.
- Added a frozen TEST_ONLY evidence-uncertainty calibrator using the existing Claude shadow benchmark history. Three successes in three observations produce a 95% Wilson interval `[0.438503, 1.0]`; the frozen minimum-sample/lower-bound rule correctly returns `INSUFFICIENT_EVIDENCE`, creates only a SHADOW candidate, and prevents production promotion or rerun-based threshold shopping.
- Added exact-checkpoint real-work preemption and material-wake recovery to Task Continuity plus regressions for park eligibility, provenance, statistical stopping rules, idempotence, and preempt/resume behavior. Targeted tests passed 30/30; full suite passed 517/517 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 passed.

## Unreleased — ZERO scientific learning bootstrap (2026-08-30)

- Added one lean, hash-sealed scientific learning module integrated with the existing Task Continuity lifecycle. It records knowledge objects, prerequisite edges, official-source provenance, bounded assessments, error memory, contradictions, confidence vectors, and explicit non-trust states without introducing a scheduler, learning control plane, or dependency.
- Completed durable campaign `learning-bootstrap-001`: 11/11 frozen units passed their bounded first-cycle diagnostics. Eight units are `PROBLEM_TESTED`; binary/architecture/testing units are `APPLIED`; zero units are `TRUSTED`.
- Ran one TEST_ONLY application comparing naive and fixed-width Windows status-code normalization. Both signed `-1073741510` and unsigned `3221225786` resolve to `0xC000013A`; this is retained only as `CAPABILITY_CANDIDATE` and production routing is unchanged.
- Preserved `DEFENSIVE_AUTHORIZED_ONLY`, zero external writes, zero financial actions, zero unauthorized cyber actions, version 0.21.0, V0.30 waiting state, L0, and 0 KWD. Targeted integration passed 75/75; full suite passed 507/507 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 passed.
- Extended the existing Task Continuity store with bounded, append-preserving `RehydrationPacket` records for Work-session rollover. Packets are atomic, hash-sealed, task-bound, tamper-detecting, idempotent for unchanged state, and cannot misrepresent a completed task as active. The completed scientific campaign now has a real durable rollover packet; no new Supervisor or control plane was added.

## Unreleased — Task Continuity V1.1 runtime integration and live chaos proof (2026-08-30)

- Added one provider-neutral durable task engine with task/session/checkpoint records, hash integrity, atomic replacement, OS cross-process locking, CAS revisions, single-writer ownership, bounded recovery, explicit blocker policy, repository reconciliation, authority reconciliation, and read-only status.
- Integrated lifecycle facts into the existing Supervisor and both backend routes while keeping Host Verification authoritative. Claude's owned run ID/PID can be observed and cancelled without recursive or unrelated process termination; backend, transport, and upstream provider are recorded independently.
- Added an isolated real-Claude chaos proof: the first owned session was terminated after a material checkpoint, and a fresh session resumed the same Task ID, skipped the completed step, changed only the unfinished file, preserved repository/unrelated-file truth, and passed Host Verification. No external or financial action occurred.
- Added Task Continuity regressions covering atomic-write interruption, corruption/truncation, thread and real multi-process CAS races, stale owner, restart reconstruction, retry/switch limits, repository drift, terminal authority, backend substitution, transport separation, and Host Verification gating. Full suite: 502/502 PASS with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 PASS. Version remains 0.21.0.

## Unreleased — ZRWVE V1.2J bounded public reality watch (2026-08-29)

- Added a single Wake Plane-integrated, read-only Reality Source Registry for the frozen T2 target. It observes only the explicitly authorized public Prefect and Apache Airflow issue surfaces with conditional ETag requests, updated-at cursors, bounded rate/backoff policy, source checkpoints, immutable incident versions, and no model polling or external writes.
- Added deterministic incident normalization/qualification, structural clustering, owner/bot/duplicate/provenance gates, prompt-injection containment, decision-time/outcome separation, B3 baseline advocacy, Minimal ZERO composition, same-evidence hashes, human-only-when-necessary contracts, append-only corrections, and status/history commands. Raw issue text is never retained.
- Historical replay passed on four structural T2 incidents and rejected two simple/generic incidents. The live canary initially surfaced Prefect #22964; classifier revision V2 correctly reclassified it as an observer/logging noise issue and closed its provisional human contract without deleting history. The second canary remains healthy with zero qualified incidents, zero Wake requests, zero external writes, and zero model calls.
- Existing Wake Plane was gracefully restarted to load the adapter and now reports `ACTIVE_READ_ONLY` for the reality-watch route while remaining `PASSIVE_PRODUCTION`; V0.30, E2-01, ZERO-INBOUND-001, L0, 0 KWD, and version 0.21.0 are unchanged.
- Added `tests/test_real_world_value_reality_watch.py` and regressions for source registry, bounded polling, ETag/reclassification, malformed/rate-limit/corrupt state, dedupe, qualification, clustering, evidence freeze, B3/Minimal ZERO parity, human contracts, prompt injection, privacy, and Wake integration.

## Unreleased — ZRWVE V1.2H passive intake publication and read-only routing (2026-08-29)

- Consumed the exact bounded publication authorization by adding only `.github/ISSUE_TEMPLATE/real-incident-intake.yml` to the separate public `agent-runtime-audit` repository at commit `bac95d4eafe3180638d90694539e902aa375b723`. Independent API verification confirmed one changed file and the frozen content hash; no message, mention, comment, outreach, advertising, paid promotion, or unrelated external modification occurred.
- Integrated the existing read-only GitHub detector with the two-stage V1.2H validators. Form submissions are separated from generic ZERO-INBOUND events, bound to immutable GitHub actor and revision provenance, chain-deduplicated, privacy-minimized, and fail closed on owner/bot/duplicate/secret/spam/prompt-injection inputs. Raw issue bodies are never journaled.
- Registered the two bounded Wake Plane trigger types and resumed the existing scheduled Wake Plane in `PASSIVE_PRODUCTION`. The V1.2H route is `ACTIVE/READY`; the first real poll found 0 issues/submissions and therefore produced no Wake request or evidence promotion.
- Targeted tests passed 38/38, relevant regressions passed 69/69, and the final full suite passed 441/441 with ResourceWarning-as-error. Publication is not independent discovery or T2 evidence; L0, 0 KWD, V0.30 waiting, and version 0.21.0 remain unchanged.

## Unreleased — ZRWVE V1.2H passive real-incident intake design (2026-08-29)

- Compared six passive intake surfaces against the frozen V1.2E–G evidence and current read-only public-repository state. Selected one two-stage GitHub Issue Form by transparent score; repository documentation and a static guide lack an attributable submission route, Discussions are disabled, dedicated email has higher privacy/moderation cost and cannot reuse E2-01, and changing the Action surface would contaminate ZERO-INBOUND-001.
- Added local Stage 1 qualification, strict Issue Form parsing, trusted source observations, hashed internal identity/dedupe, opinion/spam/owner/bot/anonymous/secret/prompt-injection firewalls, Stage 2 E1/E2/E3/E4 reuse, blind-experiment compatibility, and design-only normalized Wake events. No source was registered with the Wake Plane and no submission can grant authority or promote demand/value.
- Froze the exact one-file publication packet for `.github/ISSUE_TEMPLATE/real-incident-intake.yml` as `FROZEN_NOT_AUTHORIZED_NOT_PUBLISHED`, with content/schema/event hashes, privacy and moderation policy, 30-day review boundary, one-commit rollback, discovery limitations, and one future external write. Publication/external writes/messages remain 0 and authority remains false.
- V1.2H tests passed 11/11; relevant packet, binding, participant-discovery, Wake-source, and Wake Plane regressions passed 64/64 with ResourceWarning-as-error. Syntax, diff, concrete-secret, and independent publication-absence checks passed. Evidence remains L0, value 0 KWD, V0.30 `WAITING_EXTERNAL_EVIDENCE`, and version 0.21.0.

## Unreleased — ZRWVE V1.2G qualified participant discovery (2026-08-29)

- Added a bounded, read-only discovery cycle over the frozen T2 incident corpus and first-party public identity evidence. Six serious candidates were reviewed and ranked transparently; each is `QUALIFIED_BUT_NOT_CONTACTABLE` because only a public GitHub profile was verified and no legitimate one-to-one professional route was exposed.
- Preserved the V1.2F packet, initial-message, participant-set, expiry, dedupe, privacy, no-follow-up, no-secrets, and no-financial-authority boundaries. Zero participants were selected or bound, no private contact was inferred, and no external write, message, or E2-01 reuse occurred.
- Added `value-deep-participant-discovery`, idempotent numbered artifact handling, discovery dossiers, saturation and RED records, and six discovery regressions plus a CLI smoke test. Targeted/CLI verification passed 15/15; full regression passed 425/425 with ResourceWarning-as-error; compile, benchmark, release 5/5, stability 11/11, secret, diff, and authority gates passed. Version remains 0.21.0, evidence L0, economic value 0 KWD, and V0.30 remains `WAITING_EXTERNAL_EVIDENCE`.

## Unreleased — ZRWVE V1.2F channel and participant binding (2026-08-29)

- Added a local-only channel/participant binding layer for the frozen T2 incident experiment. Gmail is
  discovered as a transport capability but the existing E2-01 authorization is explicitly not reused; no
  send, draft, reply, or network write is performed.
- Ranked six T2 public incident records with transparent relevance, evidence, independence, contact-route,
  stack, privacy, and utility fields. All fail closed because the corpus has no attributable independent
  actor plus legitimate one-to-one contact route; no private contact data is inferred and no participant is
  bound. The resulting state is `READY_TO_BIND_BUT_NO_QUALIFIED_PARTICIPANT`.
- Froze participant-set, message, packet, expiry, dedupe, privacy, owner-control, financial, secret,
  follow-up, and ZRWVE-only thread policies. Persisted capability, candidate, binding, and host-verification
  artifacts under `.omega/zero/`; `EXTERNAL_ACTION_AUTHORIZED=false`, messages sent 0, evidence L0, and value
  0 KWD remain unchanged.
- Binding/CLI verification passed 17/17; full regression passed 418/418 with ResourceWarning-as-error;
  compile, benchmark, release 5/5, stability 11/11, secret, diff, and authority gates passed. Version
  remains 0.21.0 and V0.30 remains `WAITING_EXTERNAL_EVIDENCE`.

## Unreleased — ZRWVE V1.2E external incident packet hardening (2026-08-29)

- Added a bounded, local hardening layer over the existing V1.2D T2 incident boundary. The packet contract now requires real sanitized incident data (E1), actual B3 configuration (E2), an ordered operator trace with judgment fields (E3), and an external verification criterion (E4), linked from incident through outcome without retrospective leakage.
- Added immutable decision-time and outcome-verification hashes, participant qualification excluding owner/OMEGA/test/bot actors, privacy/non-leading contact and one-clarification limits, blind `B3_WINS`/`ZERO_WINS`/`PARITY`/`INCONCLUSIVE` transforms, fail-closed fixture and red-team coverage, and a closed authority envelope. Test-only F1/F9/F10 are the only structural passes; F9/F10 remain classification cases rather than demand claims.
- Added the read-only `value-deep-packet-audit` command and persisted packet schemas, guide, blind transform, authority envelope, red-team report, fixtures, cycle, memory, and host-verification records under `.omega/zero/`. No network, model, Supervisor, Wake Plane, contact, account, credential, or external write was performed.
- Packet hardening completed as `READY_FOR_OWNER_AUTHORIZATION`; cycle/memory/host hashes agree. Packet regressions passed 16/16, CLI 7/7, deep regression 20/20, related ZRWVE 51/51, and the full suite 408/408 with ResourceWarning-as-error. Compile, benchmark, release 5/5, stability 11/11, secret scan, diff check, and authority gates passed. Version remains 0.21.0, evidence L0, economic value 0 KWD, and V0.30 `WAITING_EXTERNAL_EVIDENCE`.

## Unreleased — ZRWVE V1.2D deep reality acquisition (2026-08-29)

- Added a bounded twelve-pass deepening of the existing Real-World Value Engine for exactly three targets: GitOps partial deployment/revision continuity (T1), dataflow partial execution/state resume (T2), and backup/restore truth (T3). No new engine, watcher, model, external action, or production migration was introduced.
- Compiled a provenance-checked corpus of 23 primary issue/document records (15 attributable incidents, 8 baseline documents) with source/project/actor/tool/time diversity, duplicate rejection, explicit unknowns, prompt-injection DATA_ONLY treatment, and no ZERO signal/authority promotion.
- Added operator trace, B0-B3 strong-baseline, baseline-adversary, failure-structure, counterfactual, attention-burden, negative-evidence, depth-completeness, and saturation artifacts. T1/T3 are baseline wins; T2 is the only external-validation-ready target. No decision, attention, recovery, or verification delta is proven.
- Froze the attention threshold before results, a narrow max-three-participant T2 incident-acquisition packet, and a blinded B3-versus-minimal-ZERO experiment spec. External action remains unauthorized and unexecuted; Wake Plane stays PASSIVE_PRODUCTION, Capability Fabric SHADOW, global default LEGACY, evidence L0, and economic value 0 KWD.
- Added `value-deep-cycle` and read-only `value-deep-status`. Deep tests pass 20/20; related ZRWVE 51/51; Wake/Capability/Governor 39/39; ZFBR/ZFA/ZPA 14/14; Supervisor/PREB 21/21; full suite 391/391 with ResourceWarning-as-error; compile, benchmark, release 5/5, stability 11/11, secret scan, and diff checks pass. Added a CLI status smoke test (6/6 CLI tests).
- Fixed deep host-verification integrity so the persisted memory pointer is re-hashed whenever verified test results update the cycle; cycle, host-verification, and memory hashes now agree.
- Final causal decision: `EXTERNAL_INCIDENT_VALIDATION_REQUIRED`. V0.30 remains `WAITING_EXTERNAL_EVIDENCE`; the next cheapest truth is one independently attributable, privacy-safe T2 incident with actual B3 configuration, operator steps/timing, and a verifiable safe-resume criterion.

## Unreleased — ZRWVE V1.1 opportunity-frontier expansion (2026-08-29)

- Added a bounded adjacent-domain frontier extension to the existing Real-World Value Engine. It preserves eight semantic killed-wedge exclusions, compiles public problem evidence without treating it as demand, and limits the search to eight serious candidates with transparent Top-5/Top-3 scoring.
- Added an explicit Baseline Adversary covering configuration, deterministic logic, transaction boundaries, idempotency, monitoring, human review, and existing platforms. The top GitOps candidate was frozen against three strong baselines and four historical scenarios; ZERO made the same decisions, saved no verified attention, improved no reliability result, and added 54.55% complexity by the frozen proxy, so the hypothesis was killed.
- Added immutable frontier experiment hashing, multi-baseline replay, decision/attention/reliability/complexity gates, 13 RED attacks, idempotent local persistence, and read-only `value-frontier-status`. No external action, authority grant, watcher, Supervisor/Wake Plane redesign, Capability Fabric promotion, or production migration occurred.
- Added 15 frontier regressions plus one CLI regression. Frontier tests passed 15/15, related safety/CLI coverage 104/104, and the full suite 370/370 with ResourceWarning-as-error; syntax, benchmark, release 5/5, stability 11/11, diff-check, and secret scan passed. Result: `NO_UNDEFEATED_OPPORTUNITY_FOUND`, L0, 0 KWD, engine parked.

## Unreleased — ZERO Real-World Value Engine V1 (2026-08-29)

- Added a minimal deterministic value engine with explicit L0-L7 evidence levels, provenance-first evidence classification, immutable experiment hashes, baseline-first falsification, a bounded opportunity portfolio, and fail-closed value governance.
- Compiled six primary public problem reports and transparently ranked four eligible candidates without treating public pain as demand. The first frozen experiment selected cross-host recovery durability only for falsification and found the strongest ordinary baseline reached the same repair/protection decision; the hypothesis was killed for baseline parity and no external action was requested or performed.
- Added read-only `value-status`, `value-opportunities`, `value-experiments`, and `value-evidence` commands plus the bounded `value-cycle` command. Existing Wake Plane conditions are reused; no watcher, Supervisor path, authority, or production default changed.
- Added 16 adversarial ZRWVE regressions covering owner/bot/synthetic evidence rejection, provenance, dedupe, WTP-versus-settlement boundaries, frozen-threshold integrity, prompt injection, baseline parity, persistence, and non-mutating CLI reads. ZRWVE passed 16/16, related safety coverage 96/96, and full Host Verification 354/354 with ResourceWarning-as-error; syntax, benchmark, release 5/5, stability 11/11, diff-check, and secret-boundary gates passed. Evidence remains L0 and verified economic value remains 0 KWD.

## Unreleased — ZERO Capability Fabric V1 shadow routing (2026-08-29)

- Added a provider-agnostic Capability Fabric registry seeded from observable repository/host facts, with explicit availability, access mode, adoption state, provenance, limits, security, and failure fields.
- Added deterministic TaskCapabilityProfile generation, transparent route scoring, fallback graphs, verification plans, historical replay, non-authoritative shadow comparison, and low-risk controlled-routing fixtures. The router performs no execution, model call, network access, authority grant, or external action.
- Replayed nine historical work classes and three controlled internal routes with safe classification/decision parity and zero side effects. Codex CLI is recorded as `WAITING_RESOURCE` from the existing quota checkpoint; unknown adapters remain unknown. No measurable decision delta was proven, so SHADOW mode and Legacy production default remain unchanged.
- Added 15 Capability Fabric regressions and the `capability-fabric` CLI command. Capability Fabric/CLI verification passed 18/18; full Host Verification passed 337/337 with ResourceWarning-as-error; compile, benchmark, release 5/5, stability 11/11, diff-check, and concrete-secret scan passed. V0.30 remains `WAITING_EXTERNAL_EVIDENCE`, real evidence L0, and real economic value 0 KWD.

## Unreleased — ZERO Development Governor V1 (2026-08-29)

- Added a read-only deterministic Development Governor and compact source-hashed evolution checkpoint.
- Added a bottleneck map that keeps the missing independent evaluator evidence explicit while selecting only
  one reversible internal memory improvement; no external or economic evidence is promoted.
- Added four regression tests and the `development-governor` CLI command. Supervisor, Wake Plane, Gmail,
  GitHub, and all external experiment boundaries remain unchanged. Full Host Verification passed 321/321
  with ResourceWarning-as-error; compile, benchmark, release 5/5, and stability 11/11 gates passed.

## Unreleased — LZC V1.15 trusted provenance, GitHub inbound, and passive production gate

- Added a strict append-only, hash-chained V0.30 evaluator provenance journal and fail-closed independence classifier. A valid JSON file or mutable evaluator name cannot satisfy the two-evaluator gate; current independently attributable count remains zero.
- Added the read-only GitHub inbound detector for `mrmohamedhassan2017-blip/agent-runtime-audit` with repository/owner identity verification, immutable actor IDs, owner/bot exclusion, minimal content hashing, ETag/rate-limit checkpoints, bounded HTTPS GET, durable dedupe, and no write scopes. The first real poll found no qualifying inbound events.
- Extended Wake Plane trigger provenance with source event IDs and canonical fingerprints, added cross-source dedupe, and added `PASSIVE_PRODUCTION_VALIDATE_ONLY`. The existing Scheduled Task passed clean SHADOW and validate-only restart checks, then was enabled in passive production mode only; no genuine event was present and no Supervisor wake was requested.
- Preserved all external experiment boundaries, V0.30 `WAITING_EXTERNAL_EVIDENCE`, Legacy global default, ZEU `SIMULATION_ONLY`, and real economic value 0 KWD. Version remains 0.21.0.
- Added 22 targeted Wake Plane/provenance regressions, including blank-journal and rate-limit recovery. Full Host Verification passed 317/317 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 gates passed.

## Unreleased — LZC V1.9B authorized one-shot Supervisor recovery

- Used the existing `omega.supervisor.start_scheduled_task` path exactly once against the installed `\\OMEGA_Autonomous_Supervisor` task. No install, task XML/configuration, trigger, worker, Supervisor, or Core change occurred.
- Stale PID 6360 was rejected and canonical recovery removed its stale lock. A new runtime started as PID 3700 / UUID `63a10dac…`; six live samples had advancing fresh timestamps, matching heartbeat/lock identity, and Task state `Running`.
- The runtime reached the genuine V0.30 external-evidence `HARD_BLOCKER` and exited under the existing `Supervisor.run` policy after 52.083 seconds. Observed evidence was 6 timestamp advances and 7 fresh samples, below the frozen 10/10 and 60-second continuity requirements. Stop cleanup found the process already stopped and used neither `/End` nor forced termination.
- Post-run audit found that live writer enumeration and full identity result were computed but not persisted before natural exit. These values remain unproven rather than reconstructed; the recovery harness now captures them at startup for any future authorized cycle.
- Result: `SUPERVISOR_RUNTIME_RECOVERY_WITH_ISSUES`. Long-duration evidence remains `NOT_YET_PROVEN`, canary gate remains closed, and another start is not authorized by the consumed one-shot grant.
- Added four LZC V1.9B regressions. Targeted recovery/heartbeat/Supervisor/continuity checks pass 39/39; full Host Verification passes 280/280 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 gates pass.

## Unreleased — LZC V1.9A authoritative heartbeat diagnosis

- Inspected the live `Supervisor.heartbeat`, `Supervisor.run`, `Supervisor.run_cycle`, backend pulse, host-test pulse, worker entry point, atomic heartbeat replacement, error handling, configured poll cadence, runtime files, process identity, and Windows Scheduled Task state without changing runtime authority or task configuration.
- Verified that PID 6360 does not exist, the Scheduled Task is `Ready` rather than `Running`, STOP is absent, and heartbeat/lock are mutually consistent residual records from runtime UUID `b8cff1b5…`. Task Scheduler recorded last result `3221225786` (`0xC000013A`); the origin of that termination remains unproven.
- Completed an uncontaminated 300.004-second read-only diagnostic: 11/11 samples, 0 logical timestamp changes, 0 file-mtime changes, 0 fresh samples, 0 live processes, and 0 heartbeat writers. Timezone parsing, wall-clock age, mtime, path, and duplicate-file checks found no observer measurement defect.
- Result: `HEARTBEAT_STALE_EXPECTED_SUPERVISOR_NOT_RUNNING`. No repair, start, restart, lock deletion, process termination, or second writer occurred. The existing authorized recovery path must be invoked explicitly before another 60-minute read-only shadow window; the canary gate remains closed.
- Added three LZC V1.9A regressions. Targeted heartbeat/Supervisor/continuity checks pass 35/35; full Host Verification passes 276/276 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 gates pass.

## Unreleased — LZC V1.9 long-duration real Supervisor read-only shadow

- Added one isolated, non-authoritative observer for bounded heartbeat/lock/event-tail metadata. The observer performs no subprocess calls, stores no raw event content, writes only its own atomic evidence artifact, and uses an OS-level single-writer lock.
- Aborted two preliminary windows after discovering stale-heartbeat comparison and duplicate-writer defects. Fixed both before the accepted window; stopped only the four verified observer processes owned by this session, without recursive process-tree termination or any Supervisor action.
- Completed one uncontaminated 3600.012-second real window at a frozen 30-second cadence: 121/121 valid samples, 0 transient races, 0 stale-heartbeat acceptances, 0 stale-owner acceptances, 0 verification-gate mismatches, and 0 critical parity mismatches.
- All 121 samples found the same cross-file-consistent runtime identity but a stale heartbeat; 0 samples were fresh and no restart/verification/wait transition occurred naturally. A post-run audit invalidated the observer's `heartbeat_updates` count because it measured changing age rather than source timestamp changes; the metric is transparently marked `NOT_RELIABLY_MEASURED` and fixed for the next window. Result: `INCONCLUSIVE`; `LONG_DURATION_TEMPORAL_EVIDENCE` remains `NOT_YET_PROVEN` and no canary/authority-transfer gate opens.
- Added seven LZC V1.9 regressions. Targeted Lean/Supervisor verification passes 83/83; full Host Verification passes 273/273 with ResourceWarning-as-error; benchmark, release 5/5, and stability 11/11 gates pass. Version and global production default remain unchanged.

## Unreleased — LZC V1.8 Supervisor integration shadow only

- Added a pure read-only shadow adapter that maps the existing heartbeat/runtime projection to bounded non-authoritative `WOULD_*` decisions; Supervisor is not imported, modified, or invoked.
- Documented actual Supervisor entry points, state files, runtime identity, restart, dispatch, verification, error, and persistence boundaries from repository code.
- Replayed 12 lifecycle/recovery fixtures with full decision parity, deterministic replay, stale/missing/identity fail-closed behavior, Host Verification preservation, zero responsibility collisions, and zero process/network/production side effects.
- Added three LZC V1.8 regressions. Full Host Verification passes 266/266 with ResourceWarning-as-error; benchmark, release, and stability gates pass. Long-duration Supervisor shadow evidence remains unproven.

## Unreleased — LZC V1.7 real elapsed-time multi-cohort canary

- Ran a real 60.168-second foreground canary on the existing SQLite and bounded-process cohorts; no simulated elapsed time was promoted as evidence.
- Exercised mixed arrivals, idle periods, five park/wake cycles, long waits, two duplicate wake rejections, three restart snapshots, timeout boundaries, and one delayed Lean→Legacy fallback.
- Revalidated authority/resources/hash/epoch on wake and preserved both Legacy health checks, immutable SQLite verification, owned-process cleanup, reconstructable provenance, and clean architectural ownership.
- Added three LZC V1.7 regressions using explicit deterministic test-clock mode. Full Host Verification passes 263/263 with ResourceWarning-as-error; benchmark, release, and stability gates pass. Supervisor/worker behavior remains unchanged.

## Unreleased — LZC V1.6 second default cohort

- Added exactly one bounded default cohort, internal Python process execution, alongside the existing SQLite backup cohort; all other workflows remain Legacy/PARK.
- Ran 500 deterministic A/B interleaved cases, 250 per cohort, using the unchanged frozen Core API and domain-owned adapters.
- Verified 5/5 local fallbacks per cohort, 3/3 global rollbacks, healthy Legacy paths, bounded process cleanup, immutable SQLite verification, and zero cross-cohort state, selector, resource, epoch, blocker, or verifier contamination.
- Added three LZC V1.6 regressions. Full Host Verification passes 260/260 with ResourceWarning-as-error; benchmark, release, and stability gates pass. Global production default remains Legacy.

## Unreleased — LZC V1.5 extended bounded default stability

- Ran the preregistered 500-run campaign on the existing SQLite default cohort, including 300 verified backups, 25 restart/resume cases, 10 fallbacks, and five global rollback rehearsals.
- Verified zero state/selector/epoch leakage, duplicate or stale ownership, false/corrupt commits, authority violations, unexplained divergence, or Legacy-health failures.
- Full-suite load exposed a Windows WAL shared-memory lock during backup verification. Changed the completed-backup verifier to immutable read-only SQLite mode, preventing verifier-side WAL handles while retaining explicit connection closure.
- Added three LZC V1.5 regressions. Full Host Verification passes 257/257 with ResourceWarning-as-error; benchmark, release, and stability gates pass. Global default remains Legacy.

## Unreleased — LZC V1.4 bounded default-migration canary

- Added an experimental cohort-local `LEAN_DEFAULT` selector for exactly `SQLITE_STORE_BACKUP`; the global repository default remains Legacy.
- Ran 100 preregistered cases: 60 verified backups, 10 read failures, 10 write failures, five path failures, five verification failures, five restart/resume cases, and five integrity blockers.
- Verified automatic eligibility, explicit ineligible fallback/park behavior, one authoritative path, epoch-safe Lean→Legacy fallback, campaign-wide rollback, unchanged Core API, no domain leakage, and healthy Legacy operation.
- Added three LZC V1.4 regressions. Full Host Verification passes 254/254 with ResourceWarning-as-error; benchmark, release, and stability gates pass. No production-wide migration is authorized.

## Unreleased — LZC V1.3 second-workflow controlled use

- Ran 50 preregistered controlled cases on the existing `Store.backup_to` file/persistence workflow while preserving the first process-workflow evidence.
- Performed real isolated SQLite backups for success cases and fail-closed injections for read/write/path/partial/stale/verification/restart/duplicate/stale-owner/integrity/unknown cases.
- Fixed explicit SQLite verifier connection cleanup after Windows exposed a locked temporary backup during targeted tests.
- Core API remained unchanged with no domain leakage, dual authoritative execution, corrupted commit, authority violation, false success, duplicate acceptance, or stale-owner commit. Rollback and immediate Legacy fallback passed.
- Added three LZC V1.3 regressions. Full Host Verification passes 251/251 with ResourceWarning-as-error; benchmark, release, and stability gates pass.

## Unreleased — LZC V1.2 controlled selectable use

- Ran the frozen 50-run `LEAN_CONTROLLED` campaign on bounded internal Python process execution; Lean was authoritative only for campaign fixtures and Legacy remained the default.
- Normal, failure, timeout, dependency, verification, restart/resume, duplicate, stale-owner, and unknown-blocker cases passed with zero safety violations or dual-path executions.
- Rollback drill restored Legacy with state/history intact; Host Verification remained authoritative, API stability and domain isolation held, and overhead stayed LOW.
- Added three controlled-use regressions. Full Host Verification passes 248/248 with ResourceWarning-as-error. Production-wide adoption remains unauthorized.

## Unreleased — LZC V1.1 long-run selectable shadow campaign

- Executed the preregistered 100-run campaign against the frozen Lean ZERO Core API and the same bounded internal process workflow.
- Completed 10 restart, 10 timeout, and 20 resume cases with zero authority violations, false successes, duplicate executions, stale-owner commits, orphan processes, unsafe terminations, unexplained mismatches, or cross-run drift.
- API remained frozen and stable; core thinness, domain isolation, low overhead, and rollback readiness held. Result: `LONG_RUN_SHADOW_STRONGLY_SUPPORTED`; Legacy remains authoritative and production migration is not authorized.
- Added three long-run campaign regressions. Full Host Verification passes 245/245 with ResourceWarning-as-error.

## Unreleased — LZC V1 Lean ZERO Core API freeze and selectable shadow

- Froze a minimal domain-independent ZFBR API and semantic hash for intent integrity, blocker envelopes, epoch/resume gates, and verification/commit prerequisites.
- Compared legacy versus non-authoritative shadow decisions across eight bounded process cases without duplicate subprocesses, production writes, authority claims, or scheduling changes.
- API stability, blocker extensibility, unknown/self-failure containment, ownership boundaries, and rollback all passed. Result: `LEAN_ZERO_CORE_SHADOW_SUPPORTED`; legacy remains the production default.
- Added three LZC regressions. Full Host Verification passes 242/242 with ResourceWarning-as-error.

## Unreleased — ZCCE V1 ZFBR Lean ZERO Core candidate evaluation

- Evaluated the existing provider/resource, SQLite/file, and bounded process/host workflows without adding another workflow or migrating production.
- Confirmed strong general core value, medium recovery consolidation, thin generic boundaries, clean ZRL/ZAK/Supervisor ownership, optional model dependence, strong bypass resistance, low runtime overhead, and strong rollback feasibility.
- Unknown blockers fail closed and preserve frozen intent; ZFBR remains deterministic and does not become a scheduler, verifier, or evidence ledger.
- Result: `ZFBR_LEAN_ZERO_CORE_SUPPORTED`. Added three ZCCE regressions; full Host Verification passes 239/239 with ResourceWarning-as-error. Production-wide adoption remains unauthorized.

## Unreleased — ZPA V1 process/host workflow adoption

- Added an isolated ZPA harness for one bounded internal Python process execution workflow, preserving the legacy path and production firewall.
- Covered launch failure, non-zero exit, dependency, timeout, partial execution, verification failure, restart/resume, duplicate/stale ownership, cleanup safety, and rollback.
- ZFBR process adoption passed with zero authority violations, false verified successes, stale commits, duplicate accepted executions, orphan processes, or unsafe terminations. Cross-domain reuse is supported; production-wide adoption is not authorized.
- Added three process-adoption regressions. Full Host Verification now passes 236 tests with ResourceWarning-as-error; benchmark, release, and stability gates remain green.

## Unreleased — ZFA V1 one-workflow ZFBR adoption

- Added an isolated ZFA harness for the existing `Store.backup_to` SQLite file workflow, comparing legacy execution with the thin ZFBR control boundary.
- Covered normal execution, permission/path/partial-write failures, stale or mutated intent, resume/duplicate/stale-owner handling, rollback, and waiting-branch isolation; parity and fail-closed blocker classification passed.
- Fixed `FrozenWorkUnit` to deep-copy mutable specs at freeze time, preventing post-freeze input mutation from bypassing intent integrity.
- Targeted ZFA/ZFBR tests pass 11/11; full Host Verification passes 233/233 with ResourceWarning-as-error. Benchmark, release, and stability gates pass. Production-wide adoption remains unauthorized.

## Unreleased — ZFBR V1 generalized freeze/blocker/resume protocol

- Added a thin reusable `FrozenWorkUnit` primitive with immutable intent hash, execution epoch, blocker evidence, narrow repair policy, and integrity/authority/resource resume gates.
- Added distinct handling for provider quota, provider/auth/config/path/process/permission/verification failures, ambiguous external state, and frozen-spec corruption; no provider bypass, authority expansion, or hash recomputation is allowed.
- Integrated one reference ZLCA quota-blocked fixture while leaving production orchestration and all external experiments unchanged.
- Added five ZFBR regressions. Host verification passes 227 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZMER V1 Codex CLI backend diagnosis

- Compared the working CodexBackend invocation with the standalone proposal executor and ran one harmless diagnostic through each boundary.
- Root cause is provider usage/quota exhaustion (`returncode=1` in both paths), not wrapper arguments, TTY/stdio, workdir, sandbox, or timeout behavior. No provider rotation or quota bypass was attempted.
- Added safe quota/non-zero classification without persisting stderr; frozen ZLCA cases were not rerun and no model output was fabricated.
- Added one executor regression. Host verification passes 222 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZMEE V1 standalone model executor boundary

- Added a proposal-only Codex CLI executor using absolute repository context, read-only sandbox, one-call-per-case limits, strict bounded JSON output, timeout cleanup, and secret-safe metadata.
- Ran the three frozen ZLCA V1.1 cases exactly once each. All three returned `BACKEND_EXIT`; no model proposal or decision delta was accepted.
- Preserved authority, resource, Host Verification, ZRL, production, Gmail, GitHub, and economic boundaries. No external action or model-value claim occurred.
- Added three executor safety regressions. Host verification passes 221 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZLCA V1.1 model escalation value gate

- Froze three non-tailored cases across semantic ambiguity, novel bounded state, and conflicting evidence/plan gap with deterministic baselines, bounded actions, authority limits, and verification oracles.
- Added a strict injected model-executor contract; the CLI refuses to synthesize responses when no authorized standalone executor is available.
- Recorded ZLCA V1.1 as `INCONCLUSIVE` with zero actual model calls, zero fabricated decision deltas, zero authority violations, and no capability or council activation.
- Preserved the deterministic kernel as the current preferred architecture; production migration and shadow runtime remain unauthorized.
- Added four ZLCA V1.1 regressions. Host verification passes 218 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — LZP V1.1 concurrency and crash-atomicity expansion

- Added an isolated deterministic LZP-002 harness with frozen specification hash `75887dab5a050ee57bcc737a5025f6eb83f5cdf1a5359c4365e5b840731e11b5`.
- Exercised owner-epoch races, duplicate wakes, stale owners, concurrent state/resource/authority updates, verification races, 12 crash boundaries, append/state reconciliation, checkpoint recovery, 40 seeded interleavings, and accelerated long-duration scheduling.
- Preserved all constitutional invariants with zero stale-owner commits, duplicate accepted executions, authority violations, resource overcommit, and false verified successes. Ambiguous side-effect truth is explicitly parked for repair.
- Classified LZP-002 as `LEAN_CONCURRENCY_AND_ATOMICITY_PARITY_SUPPORTED`; opened the ZLCA entry gate while keeping shadow runtime and production migration unauthorized.
- Added five LZP-002 regressions. Host verification passes 214 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — Lean ZERO Parallel Control Path V1

- Added an isolated deterministic rules path and an independent imperative legacy-reference adapter; production control code, state, schemas, and external experiments remain unchanged.
- Compared identical inputs across 17 normal, failure, timeout, recovery, authority, resource, deduplication, park/wake, and novel-state scenarios.
- Achieved 17/17 decision and transition parity, 11/11 invariant preservation, zero authority violations, authoritative Host Verification, deterministic checkpoint recovery, and safe resource handling.
- Reduced model entry from an always-model comparison to one explicit `NOVEL_STATE` escalation and preserved a compact five-field append-only evidence record.
- Classified fixture complexity reduction as MEDIUM and the result as `LEAN_PATH_PARITY_WITH_MEANINGFUL_SIMPLIFICATION`; production migration remains unauthorized pending expanded concurrency/crash-atomicity coverage and shadow execution.
- Added five LZP regressions. Host verification passes 204 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Architectural Value Audit V1

- Added a machine-readable component inventory separating Safety Core, product Intelligence Core, experimental intelligence, and economic experimentation.
- Added a reversible isolated ablation fixture comparing the current selection semantics with `MINIMAL_ZERO_BASELINE`; both produced identical decisions and zero authority violations, while recovery/continuity were deliberately excluded from ablation.
- Preserved Supervisor, Host Verification, authority, process safety, continuity, provenance, external-action containment, and the working V0.21 graph product as historically earned complexity.
- Classified extended ZAK as simplify/on-demand, Capability Discovery as on-demand, compact ZRL truth integrity as Core, and unproven economic layers as parked/archived.
- Preferred `DETERMINISTIC_CORE_MODEL_ESCALATION` and `LEAN_ZERO_STRONGLY_PREFERRED`; recorded a five-phase parallel, reversible migration rather than rewriting production.
- Added four ZAVA regressions. Host verification passes 199 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Dynamic Opportunity Arena V1

- Added a frozen, deterministic 90-run benchmark spanning stable, temporal, adaptive, portfolio-pressure, negative-evidence, and resource-shock regimes at three portfolio sizes and five seeds.
- Gave ZERO and the strong dynamic-rules + scheduled-reevaluation + batched-human baseline identical events, authority, budgets, action space, deadlines, and observable outcomes.
- Recorded complete utility, regret, attention, action, verification, authority, and resource metrics plus offline-oracle scoring and minimal ablation interpretations.
- Both policies produced identical utility and regret across every run. ZERO saved 44 simulated attention minutes but used 39.5% more modeled total resources; the saving came from a directly scriptable option-creation rule.
- Classified ZDOA-001 as `ZERO_BASELINE_PARITY` with HIGH complexity tax, no demonstrated advantage, L0, and 0 KWD.
- Added three ZDOA regressions. Host verification passes 195 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Advantage Discovery V1

- Mined six killed wedge families against their strongest human, script, workflow, dashboard, SaaS, and specialist baselines.
- Identified the dominant failure pattern: baselines already close the action loop when evidence is accessible; authority, data, and integration dominate otherwise.
- Refused to promote persistence, reranking, portfolios, cross-system reasoning, capability building, or negative-evidence memory into a comparative advantage without a controlled baseline win.
- Derived a hypothetical ZERO-native task profile and one strong-baseline falsification experiment, but did not run it because no advantage survived clearly enough to authorize execution.
- Master decision is `F_ZERO_HAS_NO_DEMONSTRATED_COMPARATIVE_ADVANTAGE_YET`; evidence remains L0 / 0 KWD.
- Added three ZAD regressions. Host verification passes 192 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — VEH-001 baseline-first subscription comparison

- Froze and hashed the minimally classified owner-declared paid AI subscription without provider, account, payment, invoice, or credential data.
- Froze and hashed the strongest ordinary baseline before allowing ZERO analysis: provider subscription page, native usage dashboard, billing-cycle reminder, and manual review.
- Both baseline and ZERO selected REVIEW with no account change because usage is uncertain and avoidable value is unproven. Classified the experiment as `BASELINE_PARITY` with value exclusivity NONE.
- Killed VEH-001 under its preregistered parity rule, weakened H-VEH-001, preserved L0 / 0 KWD, and prohibited automatic repetition with another subscription.
- Added three comparison regressions. Host verification passes 189 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — VEH-001 subscription phase-one intake

- Recorded the owner-declared paid-subscription candidate without promoting it to verified value or evidence.
- Added a fail-closed phase-one state requiring exactly three non-sensitive classification fields before RAW-option or baseline freeze.
- Preserved experiment integrity: ZERO analysis, cancellation, downgrade, refund, plan modification, and every account/financial action remain blocked.
- Added two phase-one regressions. Host verification passes 186 tests; release 5/5 and stability 11/11 remain green.

## Unreleased — VEH-001 owner-option qualification

- Reviewed only repository-evidenced owner capabilities and recorded why each fails the real economic-option qualification schema.
- Recorded `VEH_NO_OPTION_AVAILABLE`; repository ownership, publication identity, mailbox capability, local compute, and simulated ledger entries were not promoted into fabricated economic options.
- Preserved baseline-first integrity: no ZERO analysis, external action, financial action, cancellation, claim, account change, or sensitive-data read occurred.
- Reclassified the active bottleneck as `OWNER_CONTROLLED_REALITY_ACCESS`; H-VEH-001 remains UNPROVEN and value remains L0 / 0 KWD.
- Added three qualification regressions. Host verification passes 184 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Master Convergence V1.1

- Registered `H-VEH-001` (`VERIFIED_ECONOMIC_OPTION_HARVESTING`) as explicitly UNPROVEN.
- Compared five time-bounded economic-option classes against native dashboards, calendars, refund portals, accountants, FinOps, and contingency recovery services; execution-gap advantage is currently weak.
- Preserved separate evidence, right, authority, permission, execution, and verified-value stages. Detection cannot create value or action authority.
- Selected exactly one master decision and project: acquire one legitimate owner-controlled test surface for `VEH-001`, then kill on baseline parity or pass only after an authorized, externally confirmed real-value delta.
- Added three convergence regressions. Host verification passes 181 tests; ResourceWarning-as-error, benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Open Problem Discovery V1

- Added a baseline-first open-problem cycle spanning 24 public evidence events across public payments, receivables, business energy, cloud/SaaS, healthcare administration, parcel refunds, tax refunds, building operations, and food inventory.
- Added explicit observed/inferred/unknown boundaries, money/resource denominators, authority/data classifications, incumbent-gap analysis, and a 20 → 10 → 5 → 3 funnel.
- Rejected false winners aggressively: native SaaS reports, accounting workflows, carrier refund tools, contingency recovery auditors, regulated healthcare/tax workflows, and integration-heavy building systems defeat or materially weaken the current candidates.
- Recorded `DISCOVERY_COMPLETE_NO_WINNER`, L0, 0 KWD, and no value exclusivity. The next bounded research action is fixture reuse/search, not infrastructure, publication, contact, or external execution.
- Added three ZOPD regressions. Host verification passes 178 tests with ResourceWarning promoted to error; benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — ZERO Machine-Native Inbound (ZMI V1)

- Added an internal machine-readable capability contract for the existing pinned CI receipt interface, including privacy, verification, provenance, cost, authority, and failure boundaries.
- Decomposed independent-evidence acquisition into eight child bottlenecks and scored them with discovery/invocation/verification friction, independence, risk, reuse, and EVSI.
- Operated one ZMI cycle: counterparty motivation is dominant because invocation, trust, and provenance are already low-friction; RED rejected a new platform and marketplace activity as busywork.
- Preserved L0, zero economic value, all existing experiments, and no external/self-generated execution.
- Added three ZMI regressions. Host verification now passes 153 tests; benchmark, release, stability, continuity, ResourceWarning, and privacy gates remain green.

## Unreleased — ZERO Reality Ledger, Hypothesis Registry, and Bottleneck Intelligence

- Added append-only Reality Ledger validation with explicit evidence/independence/value levels and rejection of unsupported promotions.
- Added persistent hypothesis registry with separate supporting, contradicting, unknown, falsification, and next-experiment fields.
- Added one operational truth cycle ingesting 12 current events without secrets or raw external data, preserving `NO_RESPONSE` and all zero-value invariants.
- Added ZBI failure cartography, bottleneck scoring, counterfactual unlocks, non-monetary capability shadow prices, capability ROI options, RED challenge, and busywork filtering.
- Current dominant bottleneck is independent evidence acquisition; the cycle executed only disciplined waiting and left WO-ZERO-001 uncontaminated.
- Added four truth-ledger and bottleneck regressions. Host verification now passes 150 tests; benchmark, release, stability, continuity, ResourceWarning, and privacy gates remain green.

## Unreleased — WO-ZERO-001 bounded public contact

- Posted exactly one transparent, non-promotional technical comment on OpenHands SDK issue #4260 under the consumed authorization.
- Recorded causal baseline/intervention/counterfactual fields, comment URL/ID, timestamp, `NO_RESPONSE`, and `REAL_EXTERNAL_ACTION` classification.
- Kept the Work Order at `PROPOSED_WORK_ORDER`; no acceptance, utility, demand, revenue, settlement, follow-up, or additional contact occurred.

## Unreleased — OMEGA Provider Resilience & Execution Broker PREB V1

- Added a machine-readable registry for the actual Codex and Host executors with explicit capability, quota, sandbox, cost, latency, and health fields; unavailable quota percentage remains `UNKNOWN`.
- Added deterministic task classification so tests, hashing, state reads, and monitoring remain Host work while reasoning/code edits remain AI-backend work.
- Added checkpoint/wake records preserving task identity, branch, frozen inputs, repository baseline, edits, tests, remaining work, backend, interruption reason, evidence hashes, and exact provider retry time.
- Added a bounded no-retry-storm policy and host-continuation/recovery simulation: quota exhaustion parks only the affected branch as `WAITING_RESOURCE`, Host completes eligible work, one availability probe occurs after wake, and the original task resumes without duplicate work.
- Added five PREB regression tests. No provider rotation, hidden credentials, policy bypass, or alternate AI provider was introduced.

## Unreleased — ZERO Counterparty + Work-Order Protocol V1

- Published and independently verified the one-file CI consumer guide at public commit `4e89d468a42492b851dcba7ce743016b6e56d3eb`; original frozen publication blobs and specification hash remain unchanged.
- Added problem-first discovery records, deterministic counterparty qualification, strict Work Order schema/lifecycle validation, and explicit `PUBLIC_PROBLEM_NOT_DEMAND` semantics.
- Operated one bounded discovery cycle across five current public runtime problems. Four passed minimum qualification; OpenHands SDK #4260 ranked first and was RED-challenged.
- Froze `WO-ZERO-001` as proposed-only plus one bounded contact authorization case. No acceptance, contact, work execution, L1-L6 promotion, or economic event occurred.
- Added PoVU only as an unproven evidence primitive and added six regressions preserving stage, provenance, authority, ZEU, and zero-value boundaries.

## Unreleased — ZERO-VALUE-BRIDGE-001

- Froze a concrete CI reliability verification unit: privacy-safe lifecycle input, deterministic bounded audit, hash-bound JSON/HTML output, reproduction method, provenance, marginal cost, benefit, and falsification conditions.
- Added a strict L0-L6 discovery-to-settlement evidence ladder and a non-owner provenance rule that prevents views, clones, bots, owner runs, and lower-level signals from being promoted.
- Added six deterministically scored acquisition routes and RED controls. A pinned public CI consumer kit won at 0.8712 without hard-coded selection.
- Prepared the minimum independent-repository consumer interface internally and created one bounded publication authorization case. No public change, workflow run, outreach, settlement, or external-evidence claim occurred.
- Added five regressions covering interface completeness, provenance independence, evidence separation, dynamic ranking, frozen inbound hash preservation, and zero-value invariants.

## Unreleased — ZERO Economic Bridge research cycle

- Added eight fully specified machine-consumable value primitives and deterministic EVA/EVSI ranking; CI reliability verification is the current research winner.
- Added an explicit internal-economy → useful output → independent consumption → external value event → real ledger evidence boundary.
- Added simulation-only conditional ZEU contracts covering escrow, success, refund, dispute, fraud challenge, double-spend rejection, and reputation without creating revenue or value.
- Froze the independent CI consumption experiment and added four regressions protecting zero-value and no-real-rail invariants.
- Recorded ZEU-X only as `UNPROVEN_RESEARCH_HYPOTHESIS`; native real token remains `NOT_JUSTIFIED`.

## Unreleased — ZERO-DISCOVERY-001 metadata activation

- Executed and publicly verified the exact approved description and seven GitHub topics without changing the public commit or triggering a workflow.
- Consumed/closed the bounded authorization and classified the metadata update as a real external action, not external evidence or demand.
- Activated the frozen discovery measurement contract with zero qualified discovery events and reranked ZAK from actual world state.

## Unreleased — ZERO-DISCOVERY-001

- Added a distinct publication → discovery → visit → intent → install-attempt → verified-install → usage → demand → WTP → payment funnel.
- Added seven auditable discovery candidates with audience, signal, reach, timing, authority friction, cost, policy risk, measurement, automation, reuse, contamination, EVA, and EVSI inputs.
- Added RED challenge, fake-engagement/busywork rejection, frozen discovery measurement semantics, and one bounded GitHub metadata authorization case.
- Added four discovery regressions, including authority-case/winner consistency and mandatory authority-friction scoring. Host verification passed 125 tests and all benchmark/release/stability gates.

## Unreleased — ZERO-INBOUND-001 bounded public experiment

- Published only the privacy-safe Agent Runtime Audit package, manual GitHub Action, fixture, frozen experiment contract/specification, tests, and hash manifest to the separately designated public repository.
- Verified public commit `159def24e9a75ef568c802d9d0fb54dd0f89db25` through an unauthenticated fresh clone, exact tree/blob hashes, public-package tests, and GitHub's active workflow record.
- Preserved the 30-day contract, immediate kill/rollback capability, zero financial authority, and explicit exclusion of owner activity, views, stars, forks, clones, and downloads from REAL evidence.
- Recorded publication as internal/derived execution evidence only and reranked ZAK without manufacturing follow-on work.

## Unreleased — ZERO-INBOUND-001 GitHub CI publication preflight

- Added the minimum manual GitHub CI audit workflow, privacy-safe fixture, and explicit REAL-evidence contract for the frozen inbound experiment.
- Bound the preflight to workflow, contract, evidence-kit, and frozen-specification hashes; added an immediate kill/rollback policy.
- Recorded the bounded publication authorization while preserving zero financial authority and rejecting views, stars, clones, downloads, owner runs, and unproven workflow successes as demand.
- Local preflight and all host gates pass. No publication was simulated or attempted because no authenticated owner-controlled GitHub publication identity/repository is available.

## Unreleased — ZAK Option-Creation Engine V1

- Added explicit `OPTION_CREATED`, `OPTION_VERIFIED`, `OPTION_EXECUTABLE`, and `OPTION_REJECTED` lifecycle states and deterministic busywork rejection.
- Added six scored `ZERO-INBOUND-001` external-truth pathways with complete unlock, value, EVSI, authority, resource, cost, risk, reversibility, truth-surface, and kill-condition contracts.
- Added RED challenge and ranking across EVA/EVSI, authority friction, time-to-signal, signal quality, automation potential, dependency risk, and future reuse without hard-coding the winner.
- Operated cycle 0003: produced a local integrity-bound evidence kit and one compact publication authority case. No publication, outreach, telemetry, revenue, or external-evidence claim occurred.
- Added five option-engine regressions. Host verification passed 121 tests plus benchmark, release 5/5, and stability 11/11.

## Unreleased — ZERO Agency Kernel Economic Foundation

- Added a minimal persistent Action/Branch Graph and `WAITING_BRANCH != WAITING_SYSTEM` scheduler law without replacing `NEXT_TASK.md` or existing runtime systems.
- Added inspectable EVA ranking, busywork rejection, RED challenge, typed Evidence Foundry records, atomic causal hypotheses, Decision Memory, resource modeling, and explicit subsystem boundaries.
- Added a simulation-only, hash-recorded, balanced ZEU ledger plus deterministic economic stress scenarios; ZEU cannot populate real economic states.
- Ran the first SHADOW decision cycle and executed its winning bounded action: freeze `ZERO-INBOUND-001` as a DERIVED, unpublished self-service installation experiment.
- Ran the next authorized ZEU stress action and preserved all results as SIMULATED evidence with no viability or monetary claim.
- Added seven ZERO kernel regressions. Host verification passed 116 tests plus benchmark, release 5/5, stability 11/11, secret scan, and continuity checks.

## Unreleased — E2-01 Preregistered Contact Batch

- Added idempotent, broker-gated execution of the four preregistered Gmail actions and per-recipient append-only send evidence.
- Verified each Gmail API receipt against the corresponding Sent-folder message without calling send acceptance a delivery or demand signal.
- Added thread-scoped reply monitoring for positive, negative, ambiguous, bounce, unsubscribe, and other evidence while excluding raw reply text from stored artifacts.
- Recorded 4/10 contacts used, four actions, zero verified deliveries, zero replies/signals, and zero KWD economic value.
- Added batch idempotency/read-only-monitor regression coverage; host verification passed 109 tests plus all benchmark/release/stability gates.

## Unreleased — Gmail Channel Activated

- Verified the real owner-approved Gmail account and exact minimum OAuth grants without sending mail.
- Persisted OAuth material using Windows DPAPI outside the repository and confirmed repository secret scans remain clean.
- Corrected Market Barrier regeneration to preserve `CHANNEL_READY`/`E2_EXECUTABLE` when supported by saved channel evidence.
- Market execution is now technically available but remains separately gated by genuine target qualification and the existing broker grant.
- Host verification passed 108 tests with ResourceWarning promoted to error; benchmark, release 5/5, and stability 11/11 pass.

## Unreleased — Secure Gmail Channel Adapter

- Added a Gmail External Action Broker adapter with Desktop OAuth loopback/PKCE and exact mailbox verification.
- Limited OAuth to `gmail.send` and `gmail.readonly`; mailbox modification and broad `mail.google.com` access are not requested.
- Added Windows DPAPI-encrypted token persistence and external-only credential paths under `%LOCALAPPDATA%\OMEGA\gmail`.
- Added a read-only readiness path and a separate broker-granted send path preserving the E2-01 hash, quota, revocation, and zero-financial-authority boundaries.
- Added eight security, broker, and state-transition regressions. Host verification passed 107 tests plus benchmark, release, and stability gates.
- Channel state remains `AUTHORIZED_PENDING_CHANNEL`: no OAuth Desktop client/token exists and no outreach was sent.

## Unreleased — E2-01 Authorization State

- Recorded the owner-approved E2-01 identity, scope, ten-contact limit, zero financial authority, expiration, and immediate kill switch.
- Frozen one honest market-contact message with SHA-256 provenance.
- Added `AUTHORIZED_PENDING_CHANNEL` so owner authorization is preserved without inventing channel configuration.
- Fixed experiment hash drift: repeated controller runs now reuse the original frozen E2 criteria verbatim.
- Host verification passed 99 tests; benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — Market Barrier Controller

- Added one-time bounded External Identity policy with identity/channel/scope/limits/revocation separation.
- Added target qualification, frozen-experiment selection, strict market-signal hierarchy, response intelligence, and negative-evidence preservation.
- Added a controller that remains `READY_FOR_AUTHORIZATION` and records zero actions until a genuine identity and channel are authorized.
- Added a rail-agnostic Treasury specification in `DISABLED` mode with isolated-signer boundaries and explicit stablecoin risks; no keys, accounts, transactions, or speculation exist.
- Host verification passed 97 tests; benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — Autonomous Founder Operating System

- Added an EVSI-per-cost Uncertainty Ledger and venture Assumption Graph; market reachability is the fatal upstream assumption.
- Separated user, champion, buyer, budget owner, security reviewer, technical approver, and economic decision maker.
- Added demand-strength calibration, Loss Memory, Board Review, reputation/treasury/unit-economics placeholders that remain empty when evidence is absent.
- Added bounded External Identity and External Action Broker contracts; credentials never imply permission and adapters do not execute without authorization.
- Added one compact minimum-authorization Decision Case with zero financial authority and a ten-contact maximum.
- Added three Capability Frontier tiers while preserving the zero-balance fund and zero verified Mission I value.
- Host verification passed 95 tests; benchmark, release 5/5, and stability 11/11 remain passing.

## Unreleased — AVF E2 and Capability Capital

- Selected coding-agent platform teams as the leading initial segment from pain, urgency, reachability, WTP hypothesis, and product-fit scoring.
- Added three positioning hypotheses and an honest competitive map covering LangSmith, Phoenix, Langfuse, Temporal, and generic process monitoring.
- Added the local-only trust package, four frozen E2 experiments, channel constraints, and a precise external-action queue.
- Added the zero-balance OMEGA Capability Investment Fund, dynamic allocation policy, Capability Frontier, separate capability/economic ROI, and no-spend investment cases.
- Verified external demand signals and Mission I economic value remain zero.
- Host verification passed 93 tests; benchmark, release 5/5, and stability 11/11 remain green.

## Unreleased — Autonomous Venture Foundry E0/E1

- Added the 50,000,000 KWD Mission I ledger invariant while keeping verified realized value at 0 KWD.
- Added 20 source-backed problem theses, reproducible opportunity scoring, five Venture Court cases, three frozen cheapest-truth experiments, portfolio state, dashboard, and capital-safety boundaries.
- Selected `agent-runtime-audit` from scoring rather than coding convenience; willingness to pay and market size remain explicitly unverified.
- Added a privacy-bounded local MVP that audits lifecycle events without exporting raw reasons, payloads, or credentials.
- Host verification passed 92 tests plus benchmark, release 5/5, and stability 11/11 gates.
- E2 remains blocked on a real qualified external demand signal; no sales, customers, revenue, cash, or valuation were fabricated.

## Unreleased — Capability Discovery Engine V1

- Added a machine-readable self model and persistent capability registry under `.omega`.
- Added historical incident analysis, three-candidate generation, reproducible value/cost/risk scoring, and frozen experiment specifications.
- Added separate objective, internal RED, internal acceptance, and external-human evidence categories.
- Accepted incident-memory preflight, evidence-boundary guard, and state-transition coverage from frozen internal experiments; limitations and disagreement remain recorded.
- Added a minimal unknown-unknown hunter that proposes experiments for unobserved transitions without changing production state.
- Host verification: 88/88 tests; benchmark, release 5/5, and stability 11/11 remain passing.
- V0.30 remains waiting for real independent evaluator evidence.

## Unreleased — V0.30 Engineering Preparation

- Added an explicit aggregation evidence gate requiring at least two distinct evaluator references.
- Clarified that ranking agreement metrics do not prove usefulness or evaluator identity.
- Added a ready-to-send independent evaluator packet and evaluator-supplied friction observation template.
- Added regression coverage preventing repeated records from one evaluator from satisfying the independence gate.
- Verified 85 tests, all benchmark gates, 5/5 release gates, and 11/11 stability gates.
- External evaluator results remain intentionally absent; V0.30 is waiting for genuine independent evidence.

## Unreleased — V0.22 Guided Onboarding and Evaluator Sessions

- Added guided first-run onboarding, packaged-example launch, and portable evaluator-session export without credentials, evidence bodies, audit payloads, identifiers, or blind-evaluation secrets.
- Changed autonomous execution so CodexBackend supplies repository edits while the trusted scheduled host runs verification with the known Python interpreter.
- Added explicit agent/change/host-test events, bounded repair feedback, a no-change gate, and genuine-failure classification.
- Added regressions proving sandbox inability to execute Python is not a hard blocker when host verification is available.
- Completed the V0.22 repository milestone on the 0.21.0 package baseline; the trusted host passed the complete 84-test suite with return code 0 and no timeout. No 0.22.0 release is claimed.

## Unreleased — Continuity System

- Added canonical project state, roadmap, architecture, runbook, and single-milestone next-task contracts.
- Added permanent AI executor, rules, and separated vision contracts under `.ai/`.
- Added fail-closed validation for corrupt state, version mismatch, stale baselines, and canonical-path drift.
- Added `project-status` and `continue` CLI commands plus a standalone Project Guardian.
- Expanded the suite to 66 passing tests, including a fresh-session continuity scenario and Windows console regression.

## 0.21.0 — 2026-08-27

- Added complete browser editing for nodes and relationships, including type changes and confirmed cascade deletion.
- Added a selectable claim inspector for evidence, confidence, assumptions, uncertainty, and falsification conditions.
- Replaced raw operation output with visual WHY, BREAK IT, PROVE IT, and WHAT IF cards and retained developer-only raw JSON disclosure.
- Added typed graph styling, visible directed relationships, zoom, pan, and fit-to-view controls.
- Added persistence and UI-contract regression coverage; all 60 tests pass.

## 0.20.0 — 2026-08-27

- Added the integrated local Core Alpha workspace served by the existing HTTP process.
- Added persisted problem creation/reopening, typed graph nodes, visible relationships, node selection, and graph connection controls.
- Connected WHY, BREAK IT, PROVE IT, and WHAT IF from the UI through the HTTP API to the deterministic Core.
- Extended claims with explicit assumptions, uncertainty, and falsifier fields.
- Migrated existing SQLite databases in place to schema version 7 with backward-compatible defaults.
- Preserved the new claim profile through API updates, canonical export/import, and declarative Problem Specs.
- Made PROVE IT consume declared uncertainty, assumptions, and falsification conditions.
- Packaged UI assets with the Python distribution.
- Added UI-serving and full UI-workflow integration coverage; 58 tests pass.
- Re-ran all benchmarks, five release gates, and 11 stability gates successfully.

## 0.11.0 — 2026-08-27

- Persist verified blind evaluation records with SHA-256 identity and append-only audit events.
- Added `/evaluations` API routes and automatic CLI `eval-score` persistence.
- Expanded the suite to 52 passing tests.
- Verified the runnable V0.1 checkpoint with benchmark, release, stability, demo, and self-audit commands; recorded the checkpoint in `PROGRESS.md`.

## 0.10.0 — 2026-08-27

- Added declarative JSON Problem Spec with stable keys and analysis target.
- Added `spec-check` validation without database mutation.
- Added `run-spec` CLI producing JSON and Markdown reports for all four operations.
- Added `POST /specs/analyze` endpoint.
- Added a launch decision example for first-use and external evaluation preparation.
- Expanded the suite from 43 to 48 tests.

## 0.9.0 — 2026-08-27

- Added append-only atomic audit events for all core mutations.
- Added explicit audit baselines when upgrading existing databases.
- Added problem updates and node/edge deletion APIs.
- Preserved delete tombstones after problem removal.
- Suppressed audit noise from no-op updates.
- Added ordered audit retrieval over HTTP.
- Raised the auditability self-claim confidence with executable evidence.
- Expanded stability audit to 10 gates and the suite from 40 to 43 tests.

## 0.8.0 — 2026-08-27

- Added blinded external evaluation case, reveal, prediction, result, and summary formats.
- Added salted label commitments and deterministic prediction replay.
- Added CLI commands for prepare, run, score, and aggregate phases.
- Added top-1, reciprocal-rank, and pairwise-agreement metrics.
- Rejects modified cases, predictions, reveals, records, and duplicate evaluation IDs.
- Added the missing external-agreement Unknown to OMEGA's own graph.
- Expanded stability audit to 9 gates and the test suite from 34 to 40 tests.

## 0.7.0 — 2026-08-27

- Extracted BREAK IT weights into validated, disclosed scoring profiles.
- Added separately stored ranking fixtures across product, incident, and science.
- Added sensitivity evaluation over four materially different profiles.
- Added a unified eight-gate Core stability audit.
- Enabled SQLite WAL mode and busy timeout.
- Added a real multi-process write stress gate with exact-count and integrity checks.
- Distinguished internal Core-candidate readiness from evidence required for V1.0.
- Expanded the suite from 29 to 34 tests.

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
- Added ZMC V1 internal motivation-compilation cycle and three regression tests; host verification now passes 156 tests with no ResourceWarning.
- Added ZDD V1 Decision Delta contract, baseline-first comparison, shadow decision twin, RED analysis, and three regression tests; host verification now passes 159 tests.
- Added URVK V1 unified reality-to-value cycle, capability inventory, falsification outcome, and two regression tests; host verification now passes 161 tests.
- Added ZAGL V1 assurance-genome discovery cycle and regression tests; upgraded-baseline comparison records BASELINE_PARITY with no unique wedge, and host verification passes 163 tests.
- Added ZABBE V1 bounded bug-bounty scope and authorization model with fail-closed tests; no external security testing performed; host verification passes 165 tests.
- Added ZAVAE V1 two-lane rights/authorization value cycle and two fail-closed regression tests; host verification passes 167 tests.
- Completed passive Intigriti program revalidation and deterministic authorization-contract hashing while preserving the active-testing firewall.
- Added ZABBE V1.3 offline hypothesis-design contract, RED/benign review, shadow states, and three safety regressions; host verification passes 170 tests.
- Added ZMI-M V1 public motivation-event analysis and two evidence-bound regressions; the audit-report wedge is weakened and host verification passes 172 tests.
- Added CCS-001 frozen continuation-safety falsification fixtures and three regressions; result is BASELINE_PARITY and host verification passes 175 tests.
# LZC V1.9C — 2026-08-28

- Froze terminal-health semantics for genuine HARD_BLOCKER exits using the recorded V1.9B episode; no runtime was started and no Supervisor behavior changed.
- Classified the 52-second episode as a healthy clean blocker exit with resumability and repeatability still unproven.
# LZC V1.9D — 2026-08-28

- Completed exactly one authorized Scheduled Task health episode. The runtime reached the genuine V0.30 blocker and exited cleanly; no second start, restart, or forced termination occurred.
- Recorded `HARD_BLOCKER_HEALTH_EPISODE_WITH_ISSUES`: writer/lock and cleanup evidence passed, but live identity capture and heartbeat progression were insufficient for a strong result.
# LZC V1.9E — 2026-08-28

- One additional authorized identity-completion episode captured full live process identity (PID 13184, creation time, executable, command, repository, heartbeat/lock UUID) and a single writer. The runtime ended in `PAUSED_FOR_APPROVAL`, not the expected V0.30 blocker; no blocker success or strong health claim was made.
# LZC V1.9F — 2026-08-28

- Froze the approval terminal path as a supported authority boundary. No Scheduled Task was started and no approval was granted. The V1.9E episode reached approval before V0.30 host verification; approval state and reason are persisted, while request identity remains unknown.
# LZC V1.9G — 2026-08-29

- Rejected only the malformed V1.9E approval record with zero authority granted and preserved its original file/event history.
- Replaced free-form approval-marker parsing with a strict single-line JSON envelope and mandatory authority fields; malformed or prompt-embedded markers no longer create approval state.
# LZC V1.9H — 2026-08-29

- Executed exactly one bounded resume transition. The malformed approval did not replay; strict parsing held; the same V0.30 work resumed and ended at a genuine clean HARD_BLOCKER with zero authority expansion, duplicate execution, or stale ownership.
- Classified as `SUPPORTED`, not strong, because the final ownership helper raced with the natural exit despite matching captured executable, command, creation time, repository, UUID, heartbeat, and lock evidence.
# LZC V1.9I — 2026-08-29

- Reclassified V1.9H live ownership from exit-race unknown to strongly supported using only persisted pre-exit evidence. No runtime was started and no production code changed.
# LZC V1.10 — 2026-08-29

- Froze a 60-minute, 3–5 episode multi-terminal observation design with parked intervals, legitimate-trigger-only starts, zero-authority observer, and fail-closed safety criteria. No campaign or runtime was started.
# LZC V1.12 — 2026-08-29

- Mapped six repository-supported wake sources and found none currently satisfied. V1.11 is preserved as supported parked stability and partial temporal evidence; no runtime or synthetic episode was started.
# LZC V1.13 — 2026-08-29

- Added a separate non-authoritative Wake Plane with strict trigger envelopes, provenance validation, durable dedupe/journal, coalescing, work routing guard, source isolation primitives, separate heartbeat/lock, stale-lock recovery, status/history commands, and Windows Scheduled Task SHADOW hosting.
- Completed real passive shadow, single-instance, heartbeat, rollback/restart, and one TEST_ONLY controlled wake. Production mode remains closed until genuine source adapters are integrated and shadow-verified.
# LZC V1.14 — 2026-08-29

- Integrated six read-only real-source detector families into the existing Wake Plane with normalized trigger output, per-source health, strict provenance, durable cross-restart dedupe, routing guard, and status visibility.
- Gmail E2 metadata and structured approval are production-ready in shadow. V0.30 provenance is blocked; GitHub inbound, provider recovery, and internal queue remain correctly dormant. Global mode remains SHADOW.

# 2026-08-31 — Cyber Expert Console + Public Gateway local V1

- Added `omega.cyber_expert`, a bounded defensive/research cybersecurity capability layer with 20 curriculum domains, safe request classification, fail-closed unsafe-request handling, and explicit non-promotion until real assessment evidence exists.
- Added `omega.public_gateway`, a local privacy-bound public-gateway fixture layer for `CODE_SCAN`, identity candidate scoring, public/private/secret component classification, and deterministic known-good/known-bad scan evidence.
- Extended CLI, API, and web UI with Cyber Expert and Public Gateway entry points while preserving existing Supervisor, Wake Plane, Task Continuity, Capability Fabric, and Host Verification boundaries.
- Verified safety and release gates: targeted tests 36/36 PASS; full suite 569/569 PASS with ResourceWarning-as-error; benchmark PASS; release gates 5/5 PASS; stability gates 11/11 PASS; diff check PASS with CRLF warnings only; non-test secret scan PASS.
- No external write, public deployment, production routing change, financial action, cyber attack, or expertise claim occurred. Version remains 0.21.0.

# 2026-08-31 — Cyber practical mastery + Public Gateway release readiness

- Added deterministic safe practical labs for all 20 cybersecurity curriculum domains, unseen-case assessments, and a frozen final exam record. The run produced `20/20` practical lab passes and `5/5` unseen assessment passes.
- ZERO Verdict remains conservative: `MASTERY_NOT_PROMOTED`. Internal practical evidence is supported, but research-grade external/novel/problem-depth evidence is incomplete.
- Added Public Gateway release-readiness checks for `PUBLIC_SAFE`, `PUBLIC_WITH_REVIEW`, `PRIVATE_RUNTIME`, and `SECRET` boundaries; API exposure; SSRF/path traversal/command injection probes; frontend secret/privileged-control inspection; and local deployment architecture.
- Public Gateway readiness is `PUSH_READY` locally with `publish_authorized=false`. No publication or deployment occurred.
- Verification passed: targeted tests 40/40; full suite 573/573 with ResourceWarning-as-error; benchmark PASS; release gates 5/5; stability gates 11/11; diff check PASS with CRLF warnings only; non-test secret scan PASS.

# 2026-08-31 — Cyber research-grade promotion mission

- Added `omega.cyber_promotion` with a frozen promotion contract, 40 novel cases across all 20 cybersecurity domains, deterministic expert-vs-baseline benchmarking, replication, stability, critical-failure checks, and independent-evidence gating.
- Added CLI/API surfaces for `cyber research-eval` and `cyber promotion-status`.
- Actual campaign result: `RESEARCH_GRADE_INTERNAL_EVIDENCE_SUPPORTED`, but promotion was refused because independent external evidence is unavailable. ZERO Verdict: `INSUFFICIENT_INDEPENDENT_EVIDENCE`.
- Metrics: correctness `1.0`; false-positive rate `0.0`; false-negative rate `0.0`; evidence quality `1.0`; uncertainty calibration `1.0`; safety score `1.0`; critical failures `0`; expert benchmark `40/40`; naive baseline `0/40`; replication `10/10`; stability `3 x 40/40`.
- No external write, financial action, unauthorized cyber action, production routing change, or expert/certified/licensed/PhD claim occurred. Version remains 0.21.0.
- Verification passed: targeted Cyber/Cyber Promotion/CLI/API tests 39/39; full suite 578/578 with ResourceWarning-as-error; benchmark PASS; release gates 5/5; stability gates 11/11; diff check PASS with CRLF warnings only; non-test secret scan PASS.

# 2026-08-31 — Cyber independent external evaluation packet

- Added `omega.cyber_external_evaluation`, a packet/freezing/status/import-validation layer for `ZERO-CYBER-INDEPENDENT-EXTERNAL-EVALUATION-V1`.
- Added CLI/API surfaces for `cyber external-eval-freeze`, `cyber external-eval-status`, `GET /cyber/external-evaluation`, and `POST /cyber/external-evaluation/freeze`.
- Created the evaluator-ready packet under `.omega/zero/cybersecurity/external_evaluation/v1/` with protocol, 14 blind challenges, scoring rubric, ground-truth commitment, schemas, journals, state, and verdict files.
- Frozen protocol hash: `9adbf37cbe750e1f1f30ff11bfa9be6c7e69666bff3896d6807a1a68ff360d85`; frozen challenge-set hash: `69fdae17e19c3b92261d49cb9aaf06ea3918445ebcccecb20a7726e460565147`.
- Fake independence is rejected explicitly: internal evaluator, Cyber Expert, owner self-test, duplicate session, wrong hashes, unverifiable provenance, safety failure, and critical failures fail closed.
- Current final state is `READY_FOR_INDEPENDENT_EVALUATOR`, not promoted. Evaluators accepted remain `0/2`; ZERO Verdict remains `INSUFFICIENT_INDEPENDENT_EVIDENCE`.

# 2026-08-31 — Public Gateway V1 autonomous build/verify mission

- Extended `omega.public_gateway` with a deterministic V1 mission runner, full PG-00..PG-12 roadmap, phase checkpoints, mission evidence, release decision, and fixture benchmark records.
- Added CLI/API surfaces for `public-gateway mission-run` and `POST /public-gateway/mission-run`.
- Actual mission result: `PUBLIC_GATEWAY_V1_VERIFIED_PUSH_READY`. The Gateway remains local and unpublished because explicit release/push authority was not granted.
- Benchmark passed: known-good `VERIFIED_CLEAN`, known-bad `NEEDS_ATTENTION`, invalid SSRF probe `FAILED`, detection coverage `1.0`, false positives `0`, false negatives `0`.
- Security/local gates passed: public request validation, SSRF/path traversal/command injection rejection, frontend secret and privileged-control scan, API exposure inspection, local deployment architecture, and publication boundary.
- No external write, financial action, production routing change, remote repository push, or deployment occurred.

# 2026-08-31 — Public Gateway V1 bounded public release

- Published exactly one static/public-safe `OMEGA-ZERO-PUBLIC-GATEWAY-V1` release surface to `mrmohamedhassan2017-blip/agent-runtime-audit`.
- Published commit: `918d4a634ecb1441a8faee36742eff73329cca41`.
- Published files were limited to `README.md` and `docs/public-gateway/*`.
- The canonical OMEGA/ZERO repository, `.omega` runtime state, OAuth/Gmail material, evaluator evidence, backend runtime, host execution controls, private logs, and secrets were not published.
- Frontend deployment is static files in the public repository. GitHub Pages was not enabled by this release. Backend deployment remains blocked pending a separate safe backend target and explicit authority.
- V0.30, Cyber Expert promotion, economic state, and production routing remain unchanged.
