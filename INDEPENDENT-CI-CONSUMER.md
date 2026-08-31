# Independent CI consumer kit

This optional template lets an independent repository run the published Agent
Runtime Audit against its own privacy-safe lifecycle event file. It installs an
immutable source commit, processes data locally inside the consumer's CI job,
and uploads the resulting reports. OMEGA and the publication owner do not need
access to the consumer repository or its event data.

This guide does not modify the frozen `ZERO-INBOUND-001` experiment or its
evidence rules. A view, clone, workflow run, or successful report is not demand,
revenue, or proof of utility. The consumer must independently decide whether the
result caused an `ACCEPT`, `REJECT`, `REPAIR`, or `NO_DECISION_VALUE` outcome.

## Input contract

- A JSON Lines file containing one object per lifecycle event.
- The `event` field must contain only a lifecycle event name.
- Do not include prompts, credentials, secrets, personal data, private source,
  raw log payloads, or confidential failure reasons.
- The consumer chooses and reviews the input file before execution.

## Minimal workflow

Copy this workflow into the independent repository and replace
`path/to/privacy-safe-events.jsonl` with its reviewed input path.

```yaml
name: Agent runtime reliability audit

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install immutable audit source
        run: >-
          python -m pip install --no-deps
          "git+https://github.com/mrmohamedhassan2017-blip/agent-runtime-audit.git@159def24e9a75ef568c802d9d0fb54dd0f89db25"
      - name: Produce bounded reliability evidence
        run: >-
          python -m agent_runtime_audit
          path/to/privacy-safe-events.jsonl
          --json-out agent-runtime-audit.json
          --html-out agent-runtime-audit.html
      - name: Record provenance receipt
        shell: python
        run: |
          import hashlib, json, os, pathlib
          source = pathlib.Path("path/to/privacy-safe-events.jsonl")
          result = pathlib.Path("agent-runtime-audit.json")
          receipt = {
              "audit_source_commit": "159def24e9a75ef568c802d9d0fb54dd0f89db25",
              "consumer_repository": os.environ["GITHUB_REPOSITORY"],
              "consumer_commit": os.environ["GITHUB_SHA"],
              "workflow_run_id": os.environ["GITHUB_RUN_ID"],
              "workflow_run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
              "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "result_sha256": hashlib.sha256(result.read_bytes()).hexdigest(),
              "utility_decision": "UNCLASSIFIED",
          }
          pathlib.Path("agent-runtime-audit-receipt.json").write_text(
              json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
          )
      - uses: actions/upload-artifact@v4
        with:
          name: agent-runtime-audit-evidence
          path: |
            agent-runtime-audit.json
            agent-runtime-audit.html
            agent-runtime-audit-receipt.json
          if-no-files-found: error
          retention-days: 30
```

The template is deliberately manual. Copying it does not authorize OMEGA or the
publication owner to trigger a consumer workflow.

## Evidence and verification contract

The consumer retains its repository identity, workflow run URL/ID, triggering
commit, workflow file hash, input hash, result hash, and the resulting utility
decision. Raw private lifecycle data need not be shared. A verifier can pin the
same audit commit, rerun the reviewed input, and compare result hashes.

Evidence levels remain separate:

- L0: public artifact exists.
- L1: independent discovery.
- L2: independent invocation or installation with non-owner provenance.
- L3: reproducible useful output tied to a real consumer decision.
- L4: independent repeat or deeper use.
- L5: explicit economic commitment or willingness to pay.
- L6: real external settlement.

Owner/OMEGA runs, bots, forks, views, clones, downloads, and lower-level signals
cannot be promoted. A run with `UNCLASSIFIED` or `NO_DECISION_VALUE` does not
establish L3 utility. The current publication provides no telemetry and cannot
observe independent use automatically.

## Failure and kill conditions

Stop and reject the result if provenance is unverifiable, the immutable source
commit changes, reproduction fails, private data would need to be disclosed, or
the output does not affect a consumer decision. The consumer can remove the
workflow and its artifacts at any time.
