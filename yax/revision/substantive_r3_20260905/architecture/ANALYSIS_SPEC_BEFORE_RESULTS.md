# Architecture audit on the fully rebuilt corrected-calendar contract

Status: **post-outcome exploratory; specified before this corrected-calendar architecture run**

The original YAX outcome and several historical architecture results were already
known when this specification was written.  In particular, the earlier
108-month lambda grid and F/G exercises exist in the repository.  This audit is
therefore not preregistered or confirmatory.  No result newly produced under the
fully rebuilt 113-month treatment and outcome contract described below may be
read before this file is committed.  The frozen v1.1 design and results remain
unchanged.

## 1. Fixed data, calendar, mapping, and estimator

The primary architecture universe is exactly the 468-occupation BASE-03 support
in `rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv`, support hash
`11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b`.
The runner must independently reconstruct the corrected cells and verify this
support, its 71-month January-2017--November-2022 preperiod weights, the Rule-A
beta values, and Webb-software normalization against the BASE-03 artifacts.

All exposure values use the existing documented Census-2018 Rule-A mapping.
The outcome calendar is the 113 observed Basic CPS months from January 2017
through July 2026 after restoring March 2017--2021 and excluding December 2022;
October 2025 is genuinely unobserved and is neither inserted nor interpolated.
The age contrast is 22--25 versus 26--65.  The estimator is the existing
grouped-binomial conditional equivalent of the two-age PPML with occupation by
age, occupation by month, and age by month fixed effects.  Employment stocks
are aggregated once using `WTFINL`; already weighted cells receive no second
survey weight.

Inference uses 9,999 occupation-cluster Rademacher wild-score multipliers with
seed `2026090551`.  The same multiplier matrix is used for every fit on the
same ordered support.  Pointwise intervals use the existing absolute
studentized wild-score critical-value rule.  Paired contrasts use the common
draw difference, its standard deviation, and its corresponding studentized
critical value.  The normal-theory two-sided 5-percent, 80-percent MDE is
`(1.959963984540054 + 0.8416212335729143) * SE`.  An interval containing zero
means only that this design does not detect a difference; it never establishes
equivalence.

## 2. Eloundou primitive identity and construction continuum

Define, before fitting,

\[
D_o=\alpha_o,\qquad S_o=\gamma_o-\alpha_o,
\qquad X_o(\lambda)=D_o+\lambda S_o,
\]

for `lambda = 0, .25, .5, .75, 1`.  The runner must fail closed unless, on all
468 occupations,

\[
\max_o|\beta_o-[D_o+.5S_o]|\le 10^{-10}.
\]

Every lambda uses the same Census mapping, ordered occupation support, corrected
preperiod employment weights, outcome cells, calendar, Webb control, estimator,
and multiplier matrix.  For each lambda, four employment-weighted,
tie-preserving raw-score cuts are computed once from the corrected preperiod
weights; these cuts and memberships are then fixed for every model involving
that lambda.  Numerical cut values may differ across lambda because the raw
score changes; the rule and inputs may not.  The categorical model contains
Q2--Q5 by post plus corrected-preperiod-standardized Webb software by post, with
Q1 omitted.  Its target is Q5 versus Q1.

Two continuous versions accompany the categorical grid:

1. **fixed beta scale:** `[X(lambda) - mean(beta)] / sd(beta)`, where both beta
   moments use the same corrected preperiod weights; and
2. **lambda-restandardized:** `[X(lambda) - mean(X(lambda))] /
   sd(X(lambda))`, with moments recomputed on the same support and weights.

The two are scale companions, not independent specifications.  At lambda .5
they must be identical.  The runner independently fits the literal Rule-A beta
categorical and continuous models and must fail unless lambda .5 reproduces the
raw scores, cuts, memberships, Webb normalization, target coefficient, and
target occupation-influence vector to `1e-10` under the identical contract.

For each lambda, preserve raw moments, cuts, complete memberships, Q1/Q5 names
and employment shares, Q5--Q1 estimates, both continuous estimates, standard
errors, intervals, MDEs, and centered draws.  Report every pairwise lambda
contrast within the categorical, fixed-scale continuous, and restandardized
continuous families using common draws.  Do not select a lambda from its
outcome estimate.

Tail diagnostics report, for adjacent lambda values and relative to lambda .5,
the complete quintile transition matrix, occupation-weighted and preperiod-
employment-weighted change shares, Q1 and Q5 intersections/unions/Jaccards, and
the named occupations leaving or entering either tail.  They are construction
diagnostics, not worker transitions and not labor-market mobility.

## 3. Computer-use and remotability diagnostics

O*NET `Interacting With Computers` importance (release 26.1, November 2021) and
Dingel--Neiman telework feasibility are static occupational characteristics,
not realized technology adoption.  Pairwise correlations with each raw
`X(lambda)` are computed using corrected preperiod employment weights on the
fixed 408-occupation complete intersection of the primary support and both
characteristics, support hash
`12e4bdcdc7958ec8a52b06762585d4887743963ddcbca7de1223b2eea44a5aca`.

The only new characteristic-conditioned outcome sequence is at lambda .5
(literal beta), on that same 408-occupation support.  Beta quintiles and all
three continuous nuisance variables are constructed once on this support with
the corrected preperiod weights.  Four models are fit regardless of direction:

1. beta quintiles plus Webb software;
2. model 1 plus O*NET computer use;
3. model 1 plus remotability; and
4. model 1 plus both computer use and remotability.

All controls enter as standardized occupation score by post terms.  Common
draws provide paired augmented-minus-base contrasts.  These are descriptive
conditioning exercises: the characteristics may be confounders, mediators, or
proxies, and coefficient survival is not causal identification of AI.

## 4. Direct D/S joint model

On the primary 468-occupation support, fit one joint linear model containing
`D by post`, `S by post`, and corrected-preperiod-standardized Webb software by
post.  Report it twice: raw D/S units and corrected-preperiod standardized D/S
units.  These are an exact re-expression of one fitted column space, not two
pieces of independent evidence.  Preserve all coefficients; the full analytic
occupation-score covariance; the full common-draw covariance; correlation
matrices; and the complete centered-draw representation.

Three prespecified linear contrasts make the scale interpretable: a one-
preperiod-weighted-SD increase in D holding S fixed, the analogous increase in
S, and a simultaneous one-SD increase in both.  The raw- and standardized-unit
versions must reproduce each contrast and its common-draw distribution to
numerical tolerance.  No D-by-S interaction, nonlinear split, or outcome-led
rotation is permitted.

## 5. Webb availability audit

The Webb audit separates conditioning from sample availability:

1. on the fixed primary 468-occupation support and fixed beta memberships, fit
   the categorical beta model with and without Webb software and report a
   common-draw paired difference;
2. construct a broader beta-valid support directly from the corrected cells,
   requiring positive January-2017--November-2022 stock for both age groups and
   finite strict Rule-A beta, but not Webb availability; recompute only this
   broader support's corrected-preperiod beta weights and quintiles, and fit the
   no-Webb model; and
3. report the broader-minus-468 no-Webb point difference as support-changing
   and descriptive, without a paired CI or an equivalence claim.

The broader rule is fixed here before its count or coefficient is read.  The
audit must list occupations and preperiod employment entering only when Webb is
not required.

## 6. Archived reparameterizations and excluded claims

Historical F/G and A/E results are retained only as a provenance and
change-of-basis audit.  The package records hashes, dates, supports, definitions,
and the algebra mapping the archived files.  It does not refit them, treat the
rotations as new scientific dimensions, or cite them as validation.  Historical
mobility/rematching analyses are not reopened, reinterpreted, or combined with
this construction audit.

## 7. Age-specific bridge limitation

The official Census 2010-to-2018 conversion proportions are total-population
shares.  Existing repository evidence contains no genuine dual-coded or other
validation sample that identifies age-specific route probabilities.  The
runner therefore writes a precise blocker identifying the searched artifacts
and preserves the existing accounting ranges/declared tilt sensitivities; it
must not estimate, impute, or label any route share as age-specific.  A new
age-specific calculation is allowed only if a versioned validation dataset with
both source and target occupation codes and age is authenticated before use.

## 8. Outputs, failure rules, and interpretation

Machine-readable outputs must include the construction identity, treatment
memberships and tail transitions, lambda estimates and common draws, paired
comparisons and MDEs, characteristic correlations and conditioning sequence,
D/S joint results and covariance, Webb-support audit, archived-history audit,
age-specific blocker, model-failure registry, input/output hashes, SCC job log,
execution receipt, and a mechanical self-check.

Abort rather than silently continue if corrected-cell construction, route-mass
conservation, calendar, input hashes, BASE-03 support/weights/memberships,
lambda-.5 identity/reproduction, common-support ordering, finite regressors,
model convergence, covariance conservation, or output-hash validation fails.
Every requested successful or failed fit remains visible.  Results describe
sensitivity of a public-CPS young-relative employment-stock association to
constructed exposure definitions.  They do not establish realized AI adoption,
causal AI effects, economic equivalence, or technology-induced mobility.
