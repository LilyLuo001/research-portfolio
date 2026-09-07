# Gate 1 numerical amendment A1 — successful replacement run

This directory retains the aggregate-only evidence from SCC job 7482383. It
contains no CPS microdata and no `aggregate_cells.csv`. The authenticated cell
artifact remained on SCC and is referenced only by its SHA-256.

## Execution identity

- Authorization commit:
  `b7c9e1c2d165c88d185cf85559f83b6329204ceb`
- Authorized implementation commit:
  `576133d86e9305726d0ceb78413fec2ac795cdb0`
- A1 specification:
  `yaxnumspec_v1_5989d8d88e772711ff47c43011e9f90f4764dc8d89230ef5486b6687f59dc05c`
- Runner SHA-256:
  `9f66a4f97ba3630fc263a06315ed5887efa99a1abf3848839d77d805d528fd8a`
- Authenticated cell SHA-256:
  `5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717`
- Numerical receipt SHA-256:
  `84aa54a8b194774cddf814baca8d13520382262373682c3732b1dbd739aa4383`
- `MODEL_AUDIT.json` SHA-256:
  `ffb4364af0bc55026fd6ebf0f0211938e71c41b382e62897263f1d437b4b8f89`
- Scheduler: `failed = 0`, `exit_status = 0`, wallclock 1,316 seconds,
  maximum virtual memory 2.246 GB.

The run started at `2026-09-07T07:53:37.263730+00:00` and finished at
`2026-09-07T08:15:14.436839+00:00`, within the committed authorization window.

## Numerical dispositions

All 11 frozen models carry `PASS_A1_NUMERICAL_CERTIFICATE`. The primary path
is trust-ncg and the distinct same-objective zero-start reference is the
independent damped sparse Newton/IRLS implementation. L-BFGS-B remains a
nonbinding contradiction diagnostic.

| model | focal target |
|---|---:|
| pooled | -0.132109451 |
| family_post | -0.021598985 |
| family_month | -0.021674952 |
| dynamics_unconditioned | -0.119888765 |
| dynamics_family_month | -0.207433689 |
| post_2020_unconditioned | -0.118069092 |
| post_2020_family_month | -0.030402197 |
| seasonal_quintile_month_unconditioned | -0.132600724 |
| seasonal_quintile_month_family_month | -0.022570213 |
| seasonal_occupation_month_unconditioned | -0.132373672 |
| seasonal_occupation_month_family_month | -0.020605758 |

These are numerical target estimates, not by themselves manuscript claims or
inference. Their interpretation remains governed by the frozen design and
downstream requirement ledger.

## Independent release guard

The post-run guard initially failed because its synthetic fixture required a
field absent from the producer's full-rank schema. The reader-only correction
and its scope are recorded in
`../../reviews/GATE1_NUMERICAL_A1_POSTRUN_GUARD_SCHEMA_CORRECTION.md`.
After that correction, the guard independently recomputed 11 certificates,
20 consumer releases, 9 downstream requirement releases, all three non-model
prerequisites, and the pre-outcome target-map byte binding.

## Sanitized transfer

`public_transfer/TRANSFER_VALIDATION.json` reports
`PASS_SANITIZED_GATE1_RECEIPT_NORMALIZATION`; all cross-receipt checks are true.
The transfer copied only schema-specific receipt projections and normalized
receipts. The terminal spec is retained as `TRANSFER_SPEC.json`.

- Terminal transfer-spec SHA-256:
  `885a9cd91113addd1d8f13ae6a1393d4a675367128968ad6dfd8754559453a94`
- Transfer-validation SHA-256:
  `26d0fc5a4456a2a63957459b6e0022255dfb8783295bdb8eec90d593b72a3000`
- Dependency-release SHA-256:
  `65db43c62b151ed06846039374ebb523702cd23a3a8465ee1035cbe4b5c43587`

No protected cell artifact was opened by the normalizer or copied here.
