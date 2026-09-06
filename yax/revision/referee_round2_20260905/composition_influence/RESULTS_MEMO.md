# Composition and influence results memo

**Status:** POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.

## Bottom line

The new regression analogue of the within-SOC2 permutation materially changes
the paper.  The corrected-calendar Q5--Q1 coefficient is `-0.134554`.  Adding
SOC2-by-post controls reduces it to `-0.031474`; absorbing a separate
SOC2-specific young-relative path in every month produces `-0.031737`.  Both
intervals are wide and include zero.  The same conclusion holds on the frozen
108-month calendar.

Thus, the detailed beta classification contributes little point-estimate
magnitude after broad-family differential evolution is absorbed.  The data do
not precisely estimate the remaining within-family association.  This is
strong evidence for re-centering the employment result on broad occupational
composition, but it is not a causal decomposition: adding the family controls
changes the conditioning estimand.

The clean occupation-based exclusions do **not** support the stronger claim
that food-service recovery alone explains the pattern.  Removing Q1 food
occupations attenuates the coefficient modestly, while broader in-person-service
exclusions make it slightly more negative.  The defensible result is broad
occupational composition, not “composition plus a demonstrated food-service
mechanism.”

## 1. Broad occupational composition

All intervals below use 9,999 common occupation-level Rademacher score draws.

| Calendar and model | Q5--Q1 | 95% interval | p | Conditional information | Effective occupations |
|---|---:|---:|---:|---:|---:|
| Frozen 108 months: baseline | -0.131074 | [-0.217069, -0.045079] | .0030 | 25,675,133 | 43.30 |
| Frozen 108 months: SOC2 x post | -0.027750 | [-0.164990, 0.109489] | .7036 | 7,726,896 | 55.60 |
| Frozen 108 months: SOC2 x month | -0.028069 | [-0.164607, 0.108469] | .6996 | 7,704,734 | 55.83 |
| Corrected 113 months: baseline | -0.134554 | [-0.222160, -0.046947] | .0025 | 26,439,914 | 43.36 |
| Corrected 113 months: SOC2 x post | -0.031474 | [-0.167563, 0.104616] | .6655 | 7,953,583 | 55.69 |
| Corrected 113 months: SOC2 x month | -0.031737 | [-0.167439, 0.103965] | .6614 | 7,930,887 | 55.92 |

On the corrected calendar, SOC2-by-post controls attenuate the absolute point
estimate by 76.6 percent.  The SOC2-by-month result is nearly identical (76.4
percent attenuation).  Conditional target information falls to 30.0 percent
of baseline and the analytic cluster SE rises by about 56 percent.  The
information matrices remain full rank, so this is not a singular-fit artifact.

Support is real but narrow.  All 22 represented major groups contain at least
two beta quintiles, but only four contain both Q1 and Q5.  Consequently the
within-family coefficient is connected through intermediate quintiles rather
than being a broad direct Q5-versus-Q1 comparison in most families.  This
support fact and the much larger interval must accompany the composition
result.

Exact files:

- `results/COMPOSITION_MODELS.csv`
- `results/COMPOSITION_OCCUPATION_INFORMATION.csv`
- `results/SOC2_QUINTILE_SUPPORT.csv`
- `results/COMPOSITION_MODEL_FAILURES.json` (empty; all six fits succeeded)

## 2. Quintile profile

The frozen profile relative to Q1 is
`[0, -0.085469, -0.047792, -0.097028, -0.131074]`.

- The 3-restriction wild-score test of `b2=b3=b4=b5` has Wald statistic
  `5.7330` and `p=.1185`.  The design does not reject a common Q2--Q5 post
  coefficient; it does not establish equality.
- Q3 minus Q2 is positive (`0.037677`, SE `0.030034`), the visible violation
  of monotone decline.  The least-favorable one-sided max-t monotonicity test
  has `p=.3933`.  Its simultaneous upper bounds are not all at or below zero.
  The correct verdict is therefore **unresolved**: monotonicity is neither
  rejected nor established.

Exact files: `results/QUINTILE_PROFILE_TESTS.json` and
`results/MONOTONICITY_ADJACENT_DIFFERENCES.csv`.

## 3. Stable classification tails

Across all six original implementations, 46 occupations are always Q1 and 18
are always Q5.  Together they represent only 9.74 percent of employment on the
444-occupation common support.  The restricted always-Q5 versus always-Q1
estimate is `-0.211987`, with interval `[-0.413089, -0.010885]` and `p=.0375`.

This result shows that the negative association is present in the small stable
tails, but it is not a general rescue: the effective information count is
15.02 and the top five occupations carry 46.7 percent of target information.

Exact files: `results/STABLE_TAIL_RESULT.json` and
`results/STABLE_TAIL_MEMBERS.csv`.

## 4. Joint influence diagnostics

The top occupations are selected once using the existing frozen LOCO absolute-
movement ranking; treatment assignments and regressors are not recomputed.

| Diagnostic | Estimate | 95% interval | Deleted stock share |
|---|---:|---:|---:|
| Delete top 5 | -0.101068 | [-0.175454, -0.026682] | 4.11% |
| Delete top 10 | -0.152169 | [-0.237686, -0.066653] | 10.00% |
| Delete top 20 | -0.155539 | [-0.229636, -0.081442] | 14.33% |
| Trim 2.5% from each signed-LOCO tail (24 occupations) | -0.128088 | [-0.199327, -0.056848] | 15.67% |
| Huber down-weight above the p95 absolute-LOCO deviation | -0.131413 | [-0.199580, -0.063247] | none deleted |

Deleting the top five attenuates the magnitude by 22.9 percent.  Adding the
next five or fifteen reverses the direction of the net movement because highly
ranked occupations have opposing signed influences.  Accordingly, the joint
results establish consequential concentration but not a monotone “remove the
influential cases and the coefficient disappears” story.  The symmetric trim
and continuous down-weighting leave the estimate very close to baseline.  Both
are explicitly outcome-adaptive diagnostics, not preferred estimators.

Exact files: `results/JOINT_DELETION_AND_ROBUST_INFLUENCE.csv` and
`results/INFLUENCE_ADJUSTMENT_MEMBERS.csv`.

## 5. Food and in-person service exclusions

These definitions use Census-2018 occupation major groups and keep the frozen
quintile assignments.

| Exclusion | Occupations | Stock share | Estimate | 95% interval |
|---|---:|---:|---:|---:|
| All food preparation/service (SOC35) | 10 | 3.27% | -0.120102 | [-0.199333, -0.040872] |
| Q1 food preparation/service only | 5 | 1.17% | -0.119589 | [-0.198824, -0.040353] |
| All SOC35/37/39 in-person services | 33 | 8.20% | -0.136974 | [-0.221675, -0.052273] |
| Q1 SOC35/37/39 only | 17 | 4.89% | -0.138690 | [-0.223586, -0.053794] |

The Q1 food exclusion attenuates the absolute point estimate by 8.8 percent,
less than deleting fast-food workers alone because other Q1 food occupations
have offsetting signed influence.  Broader service exclusions do not attenuate
the result.  These results are cleaner than the IND1990 leisure/hospitality
proxy but remain occupation-side exclusions, not tests of reopening, migration,
minimum-wage, or labor-supply mechanisms.

Exact files: `results/OCCUPATION_SERVICE_EXCLUSIONS.csv` and
`results/OCCUPATION_SERVICE_EXCLUSION_MEMBERS.csv`.

## Reproducibility and limits

`results/EXECUTION_RECEIPT.json` authenticates the inputs, repair extract,
script/specification hashes, protected refs, common multiplier design, and all
result hashes.  `selfcheck.py` verifies the receipt, baseline reproduction,
full-rank fits, support counts, and output structure.  No raw CPS records or
credentials are stored here.  The corrected-calendar results restore the five
March basic samples but retain the genuinely absent October 2025 survey month.
