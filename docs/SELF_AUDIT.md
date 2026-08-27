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
