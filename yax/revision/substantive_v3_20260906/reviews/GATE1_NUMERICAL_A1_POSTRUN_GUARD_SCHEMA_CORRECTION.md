# Gate 1 A1 post-run dependency-guard schema correction

## Scope

This is a post-run reader correction. It changes neither the authorized
numerical producer nor any scientific input, treatment, support rule,
objective, target, solver, tolerance, acceptance threshold, target map, or
result byte. The replacement job ran from authorization commit
`b7c9e1c2d165c88d185cf85559f83b6329204ceb`, whose parent is implementation
commit `576133d86e9305726d0ceb78413fec2ac795cdb0`.

The guard reader was edited after protected outcomes had been opened and was
outside the pre-outcome authorization's byte binding. It is therefore recorded
as an evidence-reader correction, not represented as frozen code. The guard
SHA-256 changed from
`29f35dba1944bcb175c891a86c777aeb36adfbc62afbf5c7a09c1609e3d8eb09`
to `d52bb764dc9cf842e3469ff01d4eecd21a88dff837bf263c9a758b0dfc6d9611`.
The numerical producer and every retained result byte remained unchanged.

## Observed contradiction

SCC job 7482383 completed with scheduler `failed = 0`, `exit_status = 0`, and
an immutable receipt reporting all 11 models passed. The receipt SHA-256 is
`84aa54a8b194774cddf814baca8d13520382262373682c3732b1dbd739aa4383`;
the bound `MODEL_AUDIT.json` SHA-256 is
`ffb4364af0bc55026fd6ebf0f0211938e71c41b382e62897263f1d437b4b8f89`.

The corrected dependency guard initially rejected the same artifacts with
`numerical receipt passed_model_count mismatch`. Direct evaluation showed
that `_a1_model_is_certified` returned false for all 11 rows.

## Root cause

The guard's synthetic fixture supplied
`treatment_basis.original_columns`, and the guard required that field.
The production runner does not emit it on its full-rank branch. Instead it
emits the exact selected/dropped column partition. Therefore the guard was
testing a fixture-only field rather than the producer schema.

The dynamic models also use intentional null-basis labels in
`selected_original_labels`. Those labels must not be required to equal the
original-regressor labels textually. The load-bearing invariant is the column
partition and the dimension of each original-coefficient functional in the
current basis.

## Narrow correction

The guard now requires that:

- selected and dropped column lists contain unique integer indices;
- the two lists are disjoint and exactly partition the original columns;
- selected and dropped label-list lengths match their respective index lists;
- every original-coefficient functional has one weight per selected current-
  basis column.

The synthetic fixture now matches the runner's emitted full-rank schema and
explicitly omits the fixture-only `original_columns` field. A regression test
requires every frozen model fixture to certify in that form.

No self-reported pass flag was trusted. After the reader correction, the guard
independently recomputed all 11 certificates, all 20 consumer releases, all 9
downstream requirement releases, the three non-model prerequisites, and the
pre-outcome target-map byte binding. The result was
`PASS_ALL_11_MODELS_CERTIFIED` with no blocked model.

## Verification

- Focused guard suite: 29 passed, 9 subtests passed.
- Full repository suite at commit `d98371d5`: 1,114 passed, 3 skipped, 26
  subtests passed. Three post-run evidence tests were added in the same commit
  as this document; this commit-specific count supersedes the earlier 1,111
  count.
- Corrected guard SHA-256:
  `d52bb764dc9cf842e3469ff01d4eecd21a88dff837bf263c9a758b0dfc6d9611`.
- Corrected guard-test SHA-256:
  `3ffda2d815dc0171bb51eb35f0a59322965d60ba2bcedcba490f6a35346fca8f`.

The working requirement ledger still described T01--T03 as unvalidated during
this diagnostic invocation. The guard did not use those stale labels as pass
evidence; it authenticated the bound prerequisite artifacts directly. Ledger
reconciliation is a separate recorded step.
