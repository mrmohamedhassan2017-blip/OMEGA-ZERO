# OMEGA / ZERO Public Publication Boundary

This repository may be public, but OMEGA runtime state is not public material.

## Public-safe by default

- Source code under `omega/`, `agent_runtime_audit/`, and `src/agent_runtime_audit/`
- Tests under `tests/`
- Public documentation under `docs/`
- GitHub workflows and issue templates under `.github/`
- Top-level project documentation such as `README.md`, `CHANGELOG.md`, and `PROGRESS.md`

## Private by default

- `.omega/` runtime, wake-plane, evidence, checkpoints, journals, locks, provider records, external-evaluation packets, and experiment state
- `data/` generated or downloaded local knowledge/runtime data
- OAuth client files, tokens, credentials, refresh tokens, DPAPI blobs, and private keys
- Local host state, process identifiers, account state, private evaluator evidence, and mutable machine-only evidence

## Rule

Only explicitly classified public-safe files may be committed to a public repository.

The publication guard must fail closed for staged additions or modifications to private, secret, host-state, identity, evidence, or unknown paths. Deleting previously exposed private paths from the public tree is allowed as remediation.
