# Rebuilt-treatment dependence and inference addendum

Status: **post-outcome exploratory; written before this addendum was executed.**

This self-contained addendum applies the R3 inference audit to the canonical
rebuilt treatment contract. It does not change the frozen confirmatory design
and does not replace the historical-contract sensitivity already recorded
elsewhere.

## Fixed analysis contract

- Treatment membership is read from the authenticated
  `REBUILT_TREATMENT_MEMBERSHIP.csv` artifact produced from January 2017 through
  November 2022 stock. It must contain 468 occupations and have support hash
  `11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b`.
- The outcome panel uses the corrected Basic Monthly CPS cells, including the
  separately authenticated March 2017--2021 repair. December 2022 is the
  transition month and is excluded. October 2025 is absent and is never
  interpolated. The resulting static calendar must contain 113 observed months.
- The grouped-binomial outcome is employment stock at ages 22--25 relative to
  ages 26--65. Both models include occupation fixed effects, the four exposure
  quintile-by-post indicators, and standardized Webb software exposure-by-post.
- The pooled model absorbs calendar-month fixed effects. The conditioned model
  instead absorbs SOC2-by-calendar-month fixed effects. The target is the Q5
  versus Q1 post-January-2023 coefficient. The paired movement is conditioned
  minus pooled, on identical support.

## Broad-family dependence sensitivity

Nuisance-adjusted occupation influence contributions are aggregated to the 22
observed SOC2 families. The addendum reports CRV1-scale standard errors and
fixed-studentizer wild-score sensitivity intervals under both Rademacher and
Webb six-point multipliers. There are 99,999 draws with seed 2026090561. The
same family multiplier matrix is used for the pooled coefficient, conditioned
coefficient, and their paired movement; the stored family scores plus seed and
draw rule are a sufficient representation of the paired draw distribution.

This is a sensitivity to broad-family shock dependence, not a claim that SOC2
is the uniquely correct sampling cluster. Webb weights do not by themselves
solve every few-cluster problem.

## Corrected elapsed-calendar HAC sensitivity

Let `psi[o,t]` be the unscaled nuisance-adjusted estimator influence at
occupation `o` and observed calendar month `t`. For Bartlett lag `L`, calculate

`B_occ + HAC_L(sum_o psi[o,t]) - sum_o HAC_L(psi[o,t])`.

The third term removes the full within-occupation overlap at every lag, not
only the contemporaneous intersection. Lags are elapsed calendar months.
December 2022 and October 2025 therefore enter the January-2017--July-2026
calendar as zero-contribution placeholders. Lags 0, 1, 4, 12, and 16 are
reported. A single occupation finite factor, 468/467, is applied only after the
three unscaled meats are combined.

For every object and lag, store the full covariance matrix, its smallest
eigenvalue, its number of materially negative eigenvalues, and the target
variance. **No positive-semidefinite projection, eigenvalue clipping, or
replacement estimator is permitted.** A nonnegative target diagonal may be
shown when the full matrix is indefinite, but it must be labeled as coming from
an indefinite joint covariance and not represented as a valid joint covariance
matrix.

## Precision descriptions

For pooled, conditioned, and paired objects, report the two-sided five-percent,
80-percent-power normal approximation

`MDE80 = (z_0.975 + z_0.80) * SE`.

Report it separately for occupation clustering and SOC2-family CRV1. These are
precision descriptions, not rejection thresholds and not evidence of economic
equivalence. An interval containing zero means only that this procedure does
not detect a difference.

## Outputs fixed before execution

- `MODEL_SUMMARIES.csv`
- `OCCUPATION_INFLUENCE.csv`
- `SOC2_FAMILY_SCORE_CONTRIBUTIONS.csv`
- `SOC2_WILD_SENSITIVITY.csv`
- `CORRECTED_TIME_HAC_RESULTS.csv`
- `TIME_HAC_COVARIANCE_MATRICES.csv`
- `MODEL_FAILURES.json`
- `EXECUTION_RECEIPT.json`
- `SELF_CHECK.json`
- `FINDINGS.md`

Private microdata, person identifiers, credentials, and inaccessible absolute
paths must not be written to these artifacts.
