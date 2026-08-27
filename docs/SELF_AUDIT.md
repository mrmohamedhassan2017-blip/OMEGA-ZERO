# OMEGA Self-Audit

## Run 001 — 2026-08-27

Command: `python -m omega.cli --db data/omega-self.db self-audit`

The seeded self-graph contains 7 nodes and 6 edges. Structural validation passed with no issues. This only establishes graph integrity; it does not validate OMEGA's usefulness.

BREAK IT ranked the current risks as follows:

1. **Evidence auditability is unknown** — fragility 0.87.
2. **BREAK IT ranking may not correspond to useful attack priority** — fragility 0.81.
3. **Four node types may be insufficient for real problems** — fragility 0.72.
4. **The overall trustworthiness claim is weak** — fragility 0.70.

## Consequence

The next core increment must define a structured evidence contract with provenance and verification state, then introduce reference scenarios for evaluating ranking quality. Adding broader product layers before these tests would hide the two highest-ranked weaknesses rather than resolve them.

## Run 002 — 2026-08-27

The evidence contract is now executable and backward-compatible. Each record contains provenance, observation time, method, reliability, verification state, and a note. BREAK IT reports confidence risk, dependency risk, evidence risk, and evidence strength separately.

The first ranking benchmark contains three executable invariants:

1. Unsupported low-confidence premises rank before reproduced high-confidence premises.
2. At equal confidence, a shared dependency ranks before an isolated unknown.
3. Facts are validated or sent to PROVE IT rather than treated as BREAK IT attack targets.

Result: top-1 accuracy `1.0`, mean reciprocal rank `1.0`, 3/3 cases passed.

### Honest interpretation

These fixtures were designed from the intended semantics, so they prevent regression but cannot demonstrate real-world ranking quality. The self-graph therefore moves evidence sufficiency and ranking usefulness to `testing`, not `supported` or `resolved`.

### Next falsification target

Build independently labelled reference problems, measure agreement and ranking quality, and test sensitivity to score weights. Until then, a user must treat BREAK IT as an explainable prioritization suggestion rather than an authoritative answer.

## Run 003 — 2026-08-27

The highest-ranked taxonomy risk was tested by separating epistemic type from functional role. Twelve human-labelled reference statements cover product discovery, incident diagnosis, and scientific reasoning, with all four epistemic types represented in every domain.

Result: 12/12 type-role pairs are representable and valid. Migration from the previous schema preserves old nodes and assigns deterministic default roles.

### Honest interpretation

The test demonstrates that the two-axis ontology handles the selected cases without adding top-level types. It does not establish universal completeness, automatic classification accuracy, or agreement between independent annotators. The self-graph raises confidence in the four-type claim to 0.60 and keeps it in `testing`.

### Next falsification target

The overall trustworthiness claim is now the highest fragile node. The next increment should turn stability into explicit release gates: persistence round-trips, export/import, recovery behavior, deterministic outputs, API lifecycle coverage, and a documented completion audit.

## Run 004 — 2026-08-27

The core now has executable lifecycle gates. All five passed:

1. Repeated exports of unchanged state are byte-semantically deterministic.
2. Export/import/export preserves the canonical bundle and fingerprint.
3. Imported graphs pass structural validation.
4. Fingerprint tampering is rejected without adding a partial problem.
5. A deleted graph is recovered from a verified SQLite backup.

The transaction manager was corrected during this work: exceptions now roll back rather than reaching a commit in `finally`. A forced-failure test proves this behavior. The full suite contains 26 passing tests, including the HTTP export/import/delete lifecycle.

### Honest interpretation

These gates support storage and lifecycle trustworthiness. They do not show that WHY explanations change understanding, BREAK IT chooses the best real experiment, PROVE IT plans are sufficient, or WHAT IF impact is useful to a decision-maker. The overall claim remains `testing` at confidence 0.70.

### Next falsification target

Formalize edge semantics and operation contracts, then build independently expected end-to-end problem fixtures for all four operations. Core stability cannot be declared from storage integrity alone.

## Run 005 — 2026-08-27

Relationship and operation contract 1.0 is now executable. The `supports` direction was corrected from the earlier internal convention to the intuitive `supporter -> supported` form, with a one-time migration for existing databases.

The labelled launch-decision fixture passed 5/5 checks:

1. WHY returns prerequisites, an incoming supporter, an unresolved gap, and a contradiction.
2. BREAK IT selects the labelled weakest dependency bottleneck.
3. PROVE IT returns a falsifiable plan and the prerequisites that must be controlled.
4. WHAT IF propagates a failed prerequisite to the dependent claim.
5. All operation results declare contract version 1.0.

The complete suite now contains 29 passing tests. OMEGA's self-WHY traverses five prerequisites and one correctly directed supporting fact. The edge-semantics node moves to `supported` at confidence 0.90.

### Honest interpretation

The fixture is independently labelled relative to execution, but it remains authored inside the project. It proves implementation conformance and catches semantic regression; it does not validate ranking quality or decision usefulness with external users.

### Next falsification target

Evaluate BREAK IT weight sensitivity and ranking agreement on multiple labelled graphs whose expected priorities are stored separately from the scoring implementation. Then define an explicit Core stability checklist and audit every gate before considering V1.0.

## Run 006 — 2026-08-27

BREAK IT weights now live in a validated `ScoringProfile` and every result discloses the active values. Three labelled graphs—product, incident, and science—are stored separately from the scorer. Each expected first priority remained first under four profiles: balanced, confidence-heavy, dependency-heavy, and evidence-heavy. Robust case rate: `1.0` across 12 profile/case combinations.

The stability audit initially identified concurrent writes as an untested internal risk. OMEGA immediately attacked that result: SQLite now uses WAL plus a busy timeout, and four Python processes successfully created 32 problems and 32 nodes with exact counts and a clean integrity check.

Current result: 8/8 internal Core-candidate gates pass and 34 tests pass.

### Honest interpretation

`core_candidate_passed` is true, but `ready_for_v1` is false. The remaining blockers cannot honestly be removed by writing more expectations inside OMEGA: usefulness needs independently collected problem outcomes, and ranking needs labels not authored by the scoring project.

### Next falsification target

Create a reproducible external-evaluation protocol and an importable evaluation-record format. OMEGA can then accept blinded labels and outcomes without changing the scorer after seeing them.

## Run 007 — 2026-08-27

OMEGA now supports a complete blind-evaluation file workflow: prepare, run, reveal/score, and aggregate. Labels and evaluator references are hidden from the public case behind a salted commitment. Prediction is deterministically replayed during scoring. Changes to labels, case, or prediction fail verification, and duplicate result IDs fail aggregation.

The protocol gate passes, the stability audit is 9/9, and the suite contains 40 passing tests.

OMEGA also added the unanswered external claim to its own graph: **“Do independent evaluators agree that OMEGA priorities are useful?”** It is an Unknown with confidence 0.10 and a dependency of the overall trustworthiness claim. It should remain the highest BREAK IT target until real external records arrive.

### Honest interpretation

The machinery for honest evidence now exists, but the evidence itself does not. A self-generated successful protocol test proves integrity behavior, not independent agreement or improved outcomes.

### Next falsification target

Exercise the documented workflow on a genuinely external problem without exposing the private reveal before prediction. Until such records exist, keep V1.0 false and improve only internal usability issues that do not pretend to remove this blocker.
