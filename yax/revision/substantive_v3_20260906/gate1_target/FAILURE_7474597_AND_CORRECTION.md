# Retained T01 production failure and narrow correction

Date: 2026-09-06

## Failed execution retained

The first protected T01 execution used SCC job `7474597` against the fresh
Gate-1 cell product from job `7474594`.  Grid Engine recorded `failed=0`,
`exit_status=2`, seven seconds of wall time, and peak virtual memory of
`2.072G`.  Standard output was empty (SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852`).
Standard error had SHA-256
`dde0a0f59be2f2df97b75ee754775727663f977a1ff7b88540e6c17ed1abd805`
and contained the sanitized blocking message:

```json
{"error": "positive-weight replaced-row count is invalid", "status": "BLOCKED"}
```

The runner published no output leaf.  It authenticated and hashed the
aggregate input but stopped during producer-receipt accounting, before parsing
the aggregate cell rows or estimating any coefficient.

The sanitized scheduler projection, blocking stderr, and their source hashes
are retained under `failures/7474597/`.  They contain no restricted path,
microdata, aggregate cell value, or credential.

## Diagnosis

The successful producer receipt reports:

- `wide_march_rows_explicitly_replaced = 621589`; and
- `wide_march_positive_weight_rows_explicitly_replaced = 0`.

That zero is required by the authenticated input, not evidence of a failed
replacement.  The wide source contains the five March ASEC samples and every
record in those samples has `WTFINL=0`.  The separate March Basic source
supplies the positive-weight replacement records.  The prior R3 execution
receipt independently records the same `621589` and `0` counts, and
`survey_sim/MARCH_REPLACEMENT_FINDINGS.md` plus its self-check explicitly bind
the zero-positive-weight fact.

The producer counted the quantity correctly.  The T01 consumer incorrectly
required the positive-weight subset of superseded wide rows to be strictly
positive.  Its synthetic fixture encoded the same impossible assumption.

## Permitted correction

The correction is limited to T01 receipt validation and its immutable contract:

1. require the positive-weight count to equal the authenticated value zero;
2. make the synthetic authenticated fixture use zero;
3. add an adversarial regression case proving that a positive value is
   rejected; and
4. update the T01 runner hash and self-authenticating target-specification ID.

No cell rule, sample, exposure assignment, calendar, estimator, target, or
interpretation changes.  The protected numerical audit remains unrun.  A fresh
cell build from the corrected committed tree is required solely because T01's
Git provenance contract requires the consuming checkout to equal the producer
checkout exactly; the earlier authenticated cell product remains retained and
unchanged.
