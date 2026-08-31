# OMEGA Roadmap

Status is determined by verified implementation, not version labels alone.

## Completed

- V0.1–V0.11 — Core graph, four operations, persistence, API/CLI, audit, portability, benchmarks, evaluation protocol. Done when automated Core/recovery/stability gates passed.
- V0.20 Core Alpha — Integrated web workspace and persisted claim profiles. Done when UI-to-API workflows and reopen persistence passed.
- V0.21 Usability Hardening — Safe graph editing, visual operations, inspector, evidence UX, and graph navigation. Done with 60 tests, 5/5 release gates, and 11/11 stability gates passing.
- V0.22 Guided Onboarding and Evaluator Sessions — First-run guidance, packaged-example start, meaningful problem prompts, and privacy-safe portable evaluator sessions. Done with the complete 84-test host suite passing, including workflow persistence and the existing benchmark/release/stability coverage. The work remains unreleased on the 0.21.0 package baseline.

## Current baseline

V0.21.0 is the current verified baseline.

## LZC V1.15 — Trusted provenance and passive inbound detection

Completed as an infrastructure increment without a version bump or production-wide migration. The V0.30
provenance journal is strict and append-only; the designated GitHub repository is observed read-only with
immutable owner/actor attribution, durable dedupe, and bounded checkpoints. Shadow and validate-only gates
passed, and the existing Wake Plane is enabled in `PASSIVE_PRODUCTION` with authority `NONE`. No current
real trigger exists, so no Supervisor wake is requested.

## Next: V0.30 External Evaluator Evidence Collection

Definition of Done:

- At least two independently supplied evaluator sessions are completed against blinded cases without exposing private reveals before predictions are fixed.
- Evaluation records are portable, integrity-checked, and persist through reopen/export/import where applicable.
- Aggregate results report top-1 accuracy, reciprocal rank, pairwise agreement, and independent evaluator count without overstating usefulness.
- The repository records observed usability friction and converts it into evidence-backed follow-up work rather than expanding Core scope.
- Existing onboarding, Core regression, benchmark, release, stability, and HTTP smoke gates remain green.

## Later Core milestones

- Later V0.3x — measured usability improvements derived from V0.30 evidence.
- V1 — only after independently supplied blind evaluation and user-outcome evidence meet an explicit gate.

## Future layer order

1. OMEGA Core evidence and usability maturity.
2. Reality Compiler, only under its own approved milestone and Definition of Done.
3. WOS/World Adapters and permission model, only after Reality Compiler boundaries are proven.
4. Research directions in `.ai/VISION.md`; they are not scheduled implementation claims.
