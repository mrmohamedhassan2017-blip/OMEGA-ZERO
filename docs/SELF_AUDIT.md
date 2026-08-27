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
