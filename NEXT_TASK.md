---
baseline_version: 0.21.0
milestone: V0.30 External Evaluator Evidence Collection
status: waiting_external_evidence
---

# Next Task

## Objective

Collect honest, independently supplied evidence about whether OMEGA's priorities are useful, using the existing blind-evaluation and evaluator-session contracts without expanding beyond OMEGA Core.

## Definition of Done

- At least two independently supplied evaluator sessions are completed against blinded cases without exposing private reveals before predictions are fixed.
- Evaluation records are portable, integrity-checked, and persist through reopen/export/import where applicable.
- Aggregate results report top-1 accuracy, reciprocal rank, pairwise agreement, and independent evaluator count without overstating usefulness.
- Observed onboarding and evaluator friction is recorded as evidence and translated into bounded follow-up recommendations.
- All existing onboarding, Core regression, benchmark, release, stability, and HTTP smoke gates pass before any version bump.

## Relevant components

`omega/evaluation.py`, `omega/report.py`, `omega/store.py`, evaluator fixtures/records, documentation, and evaluation/API tests.

## Required tests

Blind-case commitment/reveal integrity, independent evaluator aggregation, evaluation persistence and portability, evaluator-session privacy regression, existing regression suite, benchmark, release-check, stability-audit, and HTTP smoke.

## Out of scope

Recruiting or impersonating evaluators, fabricating outcomes, Reality Compiler, WOS, provider/LLM integration, autonomous execution, authentication, hosted deployment, and all long-range research layers.

## Autonomous engineering checkpoint

All technically executable preparation is complete and host-verified: integrity-checked blind cases/results, persistence, aggregation metrics, an explicit two-independent-evaluator evidence gate, evaluator instructions, and an observation template. The remaining Definition of Done requires two genuine independently supplied blinded sessions plus their observed friction; OMEGA must not generate these records itself.

## Autonomous development checkpoint

The Development Governor completed bounded internal cycles and persists the latest
`development_governor_cycle_*.json` plus `evolution_checkpoint_*.json` records under `.omega/zero/`.
The primary bottleneck remains the missing independently attributable evaluator evidence; the next action is passive observation for a legitimate external event.
The Governor must run again only after a material repository/state change, so waiting is not converted into
busywork.

## Passive evidence routes

- `ZRWVE V1.2J Public Incident Watch` is an active read-only T2 observation route inside the existing Wake Plane. It may wake only for a deterministically qualified new incident or a decision-changing update; it has no external-write authority and does not alter the V0.30 milestone.
- `ZRWVE V1.2H Passive Incident Intake` remains active for voluntary operator submissions under its existing provenance and packet gates.
- E2-01 monitoring remains independent. None of these passive routes counts as V0.30 evaluator evidence, market demand, or economic value.
