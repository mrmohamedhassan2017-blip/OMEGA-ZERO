# OMEGA / ZERO Public Gateway V1

This is the bounded public release surface for `OMEGA-ZERO-PUBLIC-GATEWAY-V1`.

It provides a static, privacy-safe description of the local Public Gateway CODE_SCAN contract. It does not expose the private OMEGA/ZERO runtime, Supervisor, Wake Plane, Gmail channel, evaluator evidence, credentials, private logs, or privileged host execution controls.

## What it does

Public Gateway V1 accepts a small class of code-scan requests and returns evidence-backed verdict semantics:

- `VERIFIED_CLEAN` for a known-good fixture.
- `NEEDS_ATTENTION` for a known-bad fixture.
- `FAILED` for invalid or unsafe input.
- `UNKNOWN` when evidence is insufficient.

The released public surface is documentation and a static frontend only. Backend execution remains local/private unless a separate safe backend deployment target is explicitly authorized later.

## Evidence semantics

A displayed verdict is not customer demand, revenue, certification, security proof, or external validation. It is a bounded technical result tied to the evidence provided to the scan.

## Current deployment boundary

- Frontend: static public-safe files.
- Backend: not publicly deployed.
- Telemetry: none.
- Financial actions: none.
- External writes: this repository update only.
