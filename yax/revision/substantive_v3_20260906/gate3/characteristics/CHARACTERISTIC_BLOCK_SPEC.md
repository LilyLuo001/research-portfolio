# Gate 3 matched characteristic-conditioning specification

Status: post-outcome revision specification written before the Gate 3
characteristic-block results are computed. It does not alter the frozen v1.1
confirmatory design.

## Common contract

All models use the canonical corrected-preperiod beta quintiles and Webb
normalization already authenticated in Gate 1. Assignments and Webb units are
held fixed when support changes. Outcomes are the same 113 occupation-month
young (ages 22--25) and older (ages 26--65) employment stocks used by Gate 2;
December 2022 and nonexistent October 2025 are absent. Every model is a
grouped-binomial young-relative stock projection with occupation fixed effects.
The pooled structure absorbs calendar month; the family-month structure absorbs
SOC2 family by calendar month.

Characteristics are standardized with ages-22--65 January 2017--December 2019
employment weights on the support of the comparison in which they enter. No
postperiod outcome determines support, scaling, or labels.

## C01--C03: matched 2-by-2 computer comparison

The primary comparison uses the maximal finite O*NET computer-use-importance
support. The following four models use exactly the same occupations, rows,
quintile labels, Webb values, outcome stocks, and calendar:

| model | computer-use by post | family by calendar-month fixed effects |
|---|---|---|
| baseline | no | no |
| computer only | yes | no |
| family only | no | yes |
| combined | yes | yes |

The computer coefficient is reported per one weighted standard deviation and
per one raw O*NET importance point, with occupation- and family-cluster
covariance with Q5-by-post. Common occupation and family Rademacher multiplier
draws form pointwise intervals and covariance-preserving paired movements.
These intervals retain the Gate 3 finite-sample caveat and are not relabeled as
validated CPS design inference.

Report employment-stock coverage, fixed-effect-adjusted raw and conditional
Q5 information, their ratio, a scale-free information-matrix condition number,
the weighted beta/computer correlation, and the computer-use distribution by
fixed beta quintile. Collinearity is a precision and residual-comparison fact;
it is not a signed mechanism.

## C06: smaller common static-characteristic block

A separate complete-case support is the intersection of computer-use
importance, remotability, log wage, education requirement, routine-task
intensity, and manual/physical importance. On that one support report:

1. the unconditioned baseline;
2. each characteristic alone;
3. all six characteristics together;
4. the family-month baseline; and
5. all six characteristics in the family-month structure.

The baseline on this support identifies support-only movement before any
conditioning comparison. No coefficient that survives the controls is called
"purified AI." The historical counts are reconciled explicitly: 455 is maximal
computer support, 408 is maximal remotability support, and 341 was the earlier
intersection that also required the superseded fixed shortfalls. The current
static-only common support is computed afresh; corrected shortfalls remain in
the separately validated C05 block.

## C04: formal omitted-confounder sensitivity

Oster-style coefficient/R-squared formulas and linear omitted-variable
robustness values do not apply directly to this grouped-binomial fixed-effect
projection. No likelihood pseudo-R-squared is inserted into a linear formula.
The revision will record an applicability assessment after the matched models
are available. A separate linear companion may be reported only if its level-
share estimand, weighting, fixed effects, and selection assumptions are stated
and its result is not transferred to the nonlinear coefficient. Absence of a
defensible direct method is reported as a limit, not filled with an analogue.

## C07: industry-cell evidence

The prior CHAR-03 execution used actual occupation-by-industry-by-age-by-month
microcells, the same byte-identical canonical membership, the same outcome
calendar, and valid-industry records selected before the postperiod. Gate 3
will not rerun that unchanged protected build. A public validator must instead
authenticate the prior receipt, current membership identity, model table,
influence vectors, and paired algebra, then emit a current-contract carry-
forward result. The industry-cell baseline remains a different objective from
the occupation-month baseline; a dominant-industry occupation proxy is not a
substitute.

## Failure and interpretation rules

All requested models remain in the output denominator. Rank, separation,
convergence, or missing-support failures are serialized rather than omitted.
Coefficient attenuation is descriptive conditioning and may reflect
confounding, mediation, or proxying. Neither family nor occupational
characteristics are assigned causal shares.
