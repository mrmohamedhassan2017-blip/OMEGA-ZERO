# Agent Runtime Audit

Agent Runtime Audit is a small, local command-line tool that summarizes
lifecycle evidence from JSON Lines event logs. It identifies missing lifecycle
events and incomplete host-verification sequences without copying raw payloads,
reasons, prompts, credentials, or log lines into its reports.

This repository is the bounded public surface for the frozen
`ZERO-INBOUND-001` experiment. It is not the OMEGA source repository.

## Privacy and operation

- Processing is local and deterministic.
- There is no telemetry and the tool makes no network calls.
- Input files remain local.
- Reports contain event names/counts, findings, and limitations only.
- Raw payloads, credentials, reasons, prompts, and private log text are excluded.

Review an input before processing it. Event names themselves appear in the
report, so do not put secrets or private text in an `event` field.

## Install and run

Python 3.11 or newer is required.

```bash
python -m pip install --no-deps .
python -m agent_runtime_audit \
  experiments/ZERO-INBOUND-001/privacy-safe-events.jsonl \
  --json-out audit.json \
  --html-out audit.html
```

The JSON report contains:

- lifecycle event counts;
- required lifecycle events that were not observed;
- bounded reliability findings;
- an explicit `PASS` or `REVIEW` assessment;
- privacy and evidentiary limitations.

## Limitations

This audit does not prove process ownership, causality, customer demand,
economic value, or that unobserved actions did not happen. Its result is only as
complete as its input event stream. It is not a certification or security
guarantee.

## ZERO-INBOUND-001 evidence semantics

The manually triggered GitHub Action installs this local package, processes the
privacy-safe fixture, and emits a hash-bound technical receipt. Owner/OMEGA
runs, workflow success, views, stars, forks, clones, and downloads are not
qualified demand or independent installation evidence.

REAL experiment success requires one independently initiated external
installation attempt with verifiable external provenance and all hashes defined
in `experiments/ZERO-INBOUND-001/evidence-contract.json`. The 30-day exposure
window starts only when the public commit is independently verified.

The owner may disable the workflow and archive or remove this publication at
any time. Stop the experiment if private data is exposed, frozen hashes drift,
provenance is unverifiable, or execution requires spend or unauthorized access.
