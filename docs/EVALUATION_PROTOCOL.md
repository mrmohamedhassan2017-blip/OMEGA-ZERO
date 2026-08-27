# Blind External Evaluation Protocol

## Purpose

This protocol tests BREAK IT without changing expected priorities after seeing OMEGA's output. It provides integrity and blinding within the files; evaluator identity remains self-declared unless an external organization adds its own signature process.

## Roles

- **Evaluator:** defines a real problem graph and labels the expected attack order before prediction.
- **Runner:** receives only the public case and runs OMEGA.
- **Reviewer:** receives public case, prediction, and private reveal after prediction and verifies the result.

The roles may use separate machines or accounts. At minimum, the Runner must not receive the private reveal before producing `prediction.json`.

Evaluation commands refuse to overwrite existing output files, and preparation rejects using the same path for public and private output.

## Label file

```json
{
  "evaluator_ref": "independent-team-pseudonym",
  "expected_order": ["n2", "n0", "n3"]
}
```

Node keys come from the exported bundle. The order may cover all attackable nodes or a labelled subset, but it must contain at least one unique key.

## Integrity sequence

1. `eval-prepare` validates the bundle, generates a 256-bit random salt, and commits to evaluation ID, bundle fingerprint, labels, evaluator reference, and salt.
2. `public.json` contains the problem, locked scoring profile, and commitment—but no labels, evaluator reference, or salt.
3. `eval-run` verifies the public fingerprint and produces a deterministic prediction with its own fingerprint.
4. `eval-score` reruns the prediction, verifies exact determinism, opens the label commitment, and calculates top-1, reciprocal rank, and pairwise order agreement.
5. `eval-aggregate` rejects modified or duplicate records and aggregates verified results.

## Required external evidence record

For a result to count toward V1 evidence, archive:

- the original problem bundle and public case;
- the prediction created before reveal;
- the private reveal disclosed afterward;
- the verified result record;
- evaluator methodology and conflict-of-interest statement outside OMEGA;
- the later decision outcome, when the claim is decision usefulness rather than ranking agreement.

## Non-claims

SHA-256 commitments detect file changes but do not prove human identity, expertise, independence, or truth of the labels. High ranking agreement also does not prove that following the recommendation improved an outcome.
