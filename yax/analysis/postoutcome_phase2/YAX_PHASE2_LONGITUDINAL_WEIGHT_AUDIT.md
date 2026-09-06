# YAX Phase 2 longitudinal-weight audit

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Decision

**PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT**

The minimum patch is IPUMS CPS extract 10, generated 2026-08-31. It contains
the same 9,262,480 rows as the wide extract and adds
`LNKFW1MWT` plus merge identifiers. The row-level merge on
`YEAR MONTH SERIAL PERNUM` succeeds at 100.000%;
`CPSID`, `CPSIDP`, `CPSIDV`, `MISH`, and `AGE` agree exactly.

## Official construction and compatibility

IPUMS labels `LNKFW1MWT` as the basic-month longitudinal weight for two
adjacent months. Its documentation ties eligibility to the next-month
`CPSIDP` link. IPUMS constructs `CPSIDV` from `CPSIDP` and rejects links with
implausible changes in age, sex, or race. Therefore the defensible use tested
here is the official origin weight on the stricter CPSIDV-retained subset—not
a claim that the weight itself was constructed for CPSIDV.

| diagnostic | value |
|---|---:|
| legitimate eligible origins, ages 22–65 | 4,500,962 |
| CPSIDP adjacent matches | 4,124,467 |
| CPSIDP match rate | 91.635% |
| CPSIDV adjacent matches | 4,085,493 |
| CPSIDV match rate | 90.769% |
| positive official weight among CPSIDP matches | 100.000% |
| weighted CPSIDV retention within CPSIDP links | 98.976% |
| missing `LNKFW1MWT` | 0.000% |
| false September→November 2025 links | 0 |

The primary Phase-2 weight is consequently the origin observation's
`LNKFW1MWT` on successful validated `CPSIDV` links. Unweighted estimates are a
declared sensitivity. `WTFINL` is only a non-longitudinal sensitivity and must
not be described as correcting link selection.

The official weight does not eliminate selection caused by restricting the
sample to CPSIDV-valid links. Age, period, and beta-quintile retention and the
weighted exposure composition of retained versus rejected CPSIDP links are
reported in `YAX_PHASE2_LINK_SAMPLE_AUDIT.csv` and remain mandatory beside
coefficients.

## Link protections

- Origins are MISH 1, 2, 3, 5, 6, or 7 and destinations are exactly one
  calendar month later with MISH incremented by one.
- MISH 4→5 eight-month returns are never constructed.
- Because October 2025 is absent, September 2025 has no eligible next-month
  destination. November is never substituted.
- December 2019→January 2020 remains eligible for employment-status flows but
  will be excluded from every occupational-switching analysis.

## Scope integrity

No employment-flow outcome was constructed and no AI-flow coefficient was
estimated in this audit. A flow-analysis plan must be committed before those
outcomes are opened.
