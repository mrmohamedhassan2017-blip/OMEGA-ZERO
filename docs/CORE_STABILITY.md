# Core Stability Audit

Run:

```powershell
python -m omega.cli --db data/omega-self.db stability-audit
```

## V0.7 result

OMEGA passes all 10 internal Core-candidate gates:

1. SQLite integrity and schema version.
2. Valid persistent self-graph.
3. Ranking, taxonomy, operation, and sensitivity benchmarks.
4. Deterministic portability and backup/recovery gates.
5. Deterministic outputs from all four operations on unchanged state.
6. Explicit exclusion of WOS and Reality Compiler.
7. Operation contract version consistency.
8. Multi-process writes: four Python processes create 32 problems and nodes with no loss, duplication, lock failure, or integrity error.
9. Blind-evaluation protocol: public cases contain no labels, committed reveals verify, and modified reveals are rejected.
10. Append-only mutation audit: events exist, remain ordered, and mutation/audit writes share a transaction.

The normal test suite independently contains 43 passing tests.

## Maturity decision

`core_candidate_passed: true`

`ready_for_v1: false`

V1.0 remains blocked by evidence, not a known internal test failure:

- No independently collected user-outcome evidence shows that OMEGA recommendations improve a real decision.
- No verified blinded result from an external evaluator has been supplied yet.

These are not replaced by adding more self-authored green tests. The protocol and file formats now exist; a future external evaluation must record the problem before analysis, committed independent priorities, OMEGA output, user judgment, and whether the chosen experiment changed the decision.
