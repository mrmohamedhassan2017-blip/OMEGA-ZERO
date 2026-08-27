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
