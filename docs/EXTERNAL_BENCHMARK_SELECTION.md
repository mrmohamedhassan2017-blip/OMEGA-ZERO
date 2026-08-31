# External Benchmark Selection — V0.30

## Objective

Test whether OMEGA ranks the true bottleneck/root cause before seeing the answer. This is evidence about prioritization, not proof that OMEGA solves arbitrary real-world problems.

## First selected source: RCAEval

- Repository: https://github.com/phamquiluan/RCAEval
- Archival dataset: https://doi.org/10.5281/zenodo.14590730
- Published scope: 735 failure cases across nine microservice datasets, with ground-truth root-cause service and fault type.
- Acquisition rule: download only the case index and a small licensed subset first; do not pull the multi-gigabyte corpus until the adapter and blind protocol pass locally.

## Blind evaluation contract

1. The public case may contain system structure and pre-failure telemetry only.
2. `root_cause_service`, `fault`, injection labels, filenames that encode labels, and post-answer annotations remain private.
3. OMEGA produces a ranked list and records its scoring profile before reveal.
4. The private reveal verifies the source fingerprint and scores Top-1, reciprocal rank, and pairwise agreement.
5. Every case stores provenance, license, retrieval date, transformation version, and hashes of public/private material.
6. A case is invalid if the answer can be inferred from a path, identifier, metadata field, or preprocessing artifact.

## Acceptance threshold for the pilot

- At least 10 unseen cases from more than one fault category.
- Zero label-leakage findings in an automated audit.
- Reproducible results from a clean local database.
- Report baseline, OMEGA score, failures, and confidence intervals; do not tune and score on the same cases.

## Secondary sources

- Google Research, *Debugging Incidents in Google's Distributed Systems*: qualitative evidence for expert debugging behavior, useful for rubric design but not a labeled benchmark.
- UCI Audit Data (DOI: 10.24432/C5930Q): licensed risk-factor classification data, potentially useful for a later cross-domain test; it does not directly measure root-cause ranking.

## Decision

RCAEval is the first implementation target because it has explicit ground truth, reproducible cases, archival identity, and subset acquisition. No result from it will be called independent human validation; it is an external public benchmark only.
