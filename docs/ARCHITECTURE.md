# OMEGA System Architecture

This is the north-star architecture. Only the OMEGA Core is implemented in the current release; the downstream layers are intentionally recorded as future boundaries.

```text
OMEGA
  │
  │  The unasked question — What should we ask?
  ↓
Impossible Machine
  │  What must change?
  ↓
Reality Compiler
  │  How can it happen?
  ↓
God Mode
  │  Show me realities.
  ↓
WOS
  │  Execute safely.
  ↓
World
  │
  └── Observe result ──→ Learn ↺
```

## Current boundary

OMEGA V0.21 implements the first layer end-to-end: an integrated editable local workspace, explicit facts, assumptions, constraints, unknowns, graph semantics, evidence profiles, and visual WHY / BREAK IT / PROVE IT / WHAT IF results. It can record evidence and evaluate its own claims, but it does not execute actions in the world.

## Promotion rule

No downstream layer may be implemented merely because the preceding layer is conceptually attractive. Promotion requires reproducible tests, explicit contracts, failure handling, and evidence that the current layer solves its stated problem. Until then, the layer remains a documented hypothesis and a BREAK IT target.

## Learning loop

The eventual loop is intentionally one-way at the boundary: observe outcomes, preserve provenance, compare predictions with results, and feed only verified learning back into the graph. Unverified outcomes remain Unknowns.
