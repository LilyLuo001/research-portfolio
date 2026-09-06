# R3 dynamics findings (DYN-01--DYN-04)

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1**

This note reports the authoritative corrected-calendar run. It does not alter
the frozen estimator, reinterpret failed models as zeroes, or treat a failure to
reject as evidence of equivalence.

## What was estimated

The dynamic model uses 113 observed CPS months from January 2017 through July
2026. December 2022 is excluded as the declared transition month, October 2025
is absent and is not interpolated, and 2022Q4 (observed October and November) is
the omitted bin. Every other calendar quarter receives Q2, Q3, Q4, and Q5
interactions relative to Q1 plus a Webb-software interaction. Results are run
with occupation and calendar-month effects and, separately, occupation and
SOC2-by-calendar-month effects. Historical treatment assignments are reported
first; the corrected-preperiod rebuilt assignment is a separately labeled
sensitivity.

All four core models converged. Each has 190 slope parameters, including 152
fully interacted quintile targets. For every model, the stored 152-by-152
occupation-cluster covariance has rank 152 and is reproduced by the stored
468-occupation influence representation. All simultaneous intervals and paired
comparisons use 9,999 common occupation Rademacher score draws within treatment
contract.

## Static coefficient versus the declared dynamic functional

The dynamic functional is the observed-month-count-weighted average of the 15
post-2022 quarterly Q5-versus-Q1 coefficients. It is a companion estimand, not
an algebraic decomposition of the nonlinear grouped-binomial static coefficient.

| treatment | conditioning | static coefficient (SE; 95% CI) | dynamic functional (SE; 95% CI) | dynamic minus static (paired 95% CI) |
|---|---|---:|---:|---:|
| historical | unconditioned | -0.1346 (0.0450; [-0.2218, -0.0473]) | -0.1244 (0.0734; [-0.2674, 0.0186]) | 0.0101 ([-0.1299, 0.1501]) |
| historical | SOC2 by month | -0.0317 (0.0703; [-0.1692, 0.1057]) | -0.2126 (0.1097; [-0.4279, 0.0027]) | -0.1809 ([-0.3857, 0.0239]) |
| rebuilt | unconditioned | -0.1321 (0.0452; [-0.2216, -0.0426]) | -0.1199 (0.0733; [-0.2618, 0.0221]) | 0.0122 ([-0.1277, 0.1522]) |
| rebuilt | SOC2 by month | -0.0217 (0.0713; [-0.1607, 0.1173]) | -0.2074 (0.1111; [-0.4216, 0.0067]) | -0.1858 ([-0.3841, 0.0125]) |

The paired difference is not detected in any row. The corresponding MDE80 is
0.203 log points in the unconditioned rows and about 0.291 in the SOC2-conditioned
rows, so these comparisons do not establish equality. In particular, the large
negative conditional dynamic-minus-static point estimates are too imprecise to
resolve the mapping between the two estimands.

## Preperiod diagnostics and dynamic profile

The joint test that all 23 preperiod Q5-versus-Q1 coefficients equal zero rejects
in every model: historical unconditioned p = 0.0097, historical SOC2-conditioned
p = 0.0233, rebuilt unconditioned p = 0.0149, and rebuilt SOC2-conditioned
p = 0.0053. The maximum absolute preperiod coefficient is about 0.088--0.092
unconditioned and 0.396--0.406 under SOC2-by-month conditioning. A much less
demanding anchored linear-slope diagnostic does not reject (p = 0.830 and 0.100
historically; p = 0.812 and 0.094 rebuilt). The linear-slope result does not
override the joint rejection.

All 15 historical postperiod Q5 coefficients are negative. In the unconditioned
profile, only 2026Q2 and the observed month of 2026Q3 exclude zero under the
Q5-family simultaneous band; no SOC2-conditioned postperiod coefficient does.
The rebuilt profile has the same simultaneous-band pattern. Because the joint
preperiod diagnostics reject, these paths do not provide parallel-trend
reassurance or a clean causal onset.

## Onset, endpoint, and seasonality

Across the declared November 2022--June 2023 onset grid, the historical static
unconditioned coefficient ranges only from -0.135 to -0.128 and every interval
excludes zero. The corresponding SOC2-conditioned range is -0.035 to -0.023 and
every interval includes zero. Rebuilt assignments give the same qualitative
pattern. December 2022 and January 2023 are mechanically identical because
December is excluded in every row; both declared dates remain visible.

The post-2025 extension changes the unconditioned magnitude, though not its sign
or pointwise inference. Historically, ending in September 2025 gives -0.1117
and ending in December 2025 gives -0.1135, versus -0.1346 through July 2026.
Their paired differences from the full endpoint are 0.0229 (95% CI [0.0059,
0.0398]) and 0.0211 ([0.0058, 0.0364]). The SOC2-conditioned coefficient remains
near zero at each endpoint, and its paired endpoint differences include zero.
Excluding September and November 2025 together, or November and December 2025,
does not detectably change either full-window result. The declared post-2020
coding-stable endpoint model failed to converge in all four treatment-by-
conditioning rows and was not replaced.

Adding the predeclared 44 Q2--Q5-by-month-of-year nuisance slopes changes the
historical coefficient by -0.00034 unconditioned (paired 95% CI [-0.00403,
0.00335]) and 0.00008 under SOC2-by-month conditioning ([-0.00573, 0.00590]);
the rebuilt differences are similarly small. The saturated occupation-by-
month-of-year model failed to converge in all four rows. Those failures limit
the seasonality claim to the lower-dimensional test.

## March-source repair and retained failures

The source preflight proves that appending the 2017--2021 Basic Monthly March
repair is equivalent to replacing the unusable March ASEC rows for this stock
estimand: the wide ASEC source contributes zero analysis-eligible positive-
weight rows, the repair contributes 252,862 such rows, all five Marches have
positive stock, and no eligible CPSIDP overlaps or within-month duplicates were
found. The wide and repair input SHA-256 values are recorded in
`MARCH_REPAIR_POLICY_RECEIPT.json`.

`MODEL_FAILURES.json` permanently records eight failures: four post-2020
coding-stable endpoint models and four saturated occupation-season models. They
are failed specifications, not zero estimates.

## Rambachan--Roth sensitivity

All four event vectors pass the applicability audit: 38 Q5 coefficients (23
preperiod and 15 postperiod), an omitted 2022Q4 reference, full-rank 38-by-38
covariance, and nonnegative declared post-functional weights summing to one.
The official pinned `HonestDiD` 0.2.8 implementation is run separately; its
smoothness and relative-magnitude results and their interpretation are reported
below once the official execution receipt passes the final hash audit.

**Official-execution status:** PENDING SCC job 7469157.

## Reproducibility anchors

- Authoritative Python SCC job: 7468737 (exit 0; 2,042 seconds; 2.770 GB maximum
  virtual memory).
- Python execution receipt SHA-256:
  `98b2b0aecf64f35499a0c92eaff35cee26a3f7b97256a46cb3454360eb094e07`.
- Wide microdata SHA-256:
  `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`.
- March Basic Monthly repair SHA-256:
  `a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911`.
- Historical support: 468 occupations; support SHA-256
  `11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b`.
- Rebuilt membership SHA-256:
  `c76eb85956e4a413e130bab53fe8c50616cf6d7a02c81c266ec369879dd56bc1`.

The machine-readable coefficient paths, full covariance matrices, influence
representations, grid outputs, failure ledger, execution receipt, and self-check
sit in `results/`.
