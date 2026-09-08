# C01--C07 characteristic and industry findings

Status: post-outcome revision analysis. The characteristic block ran on SCC job
7492126 from commit `a6f448d0bf8e4f23df46b9a9a8e280a1a96970b7` and produced 14
models, 14 paired contrasts, and zero serialized failures. A public validator
reconstructed every reported model and paired interval from the retained
influence vectors; its maximum absolute numerical discrepancy was
`2.37e-15`. The industry results are an authenticated carry-forward of an
earlier protected microcell run, not a new fit.

All quantities below are descriptive young-relative employment-stock
projections. The intervals use the declared 9,999 common Rademacher multiplier
draws and retain the finite-cluster limitations established by Gate 3. Paired
confidence intervals that include zero establish nondetection, not equivalence.

## Fixed-support computer and family comparison (C01--C03)

The primary four-model collection holds fixed 455 occupations, canonical beta
quintiles, the Webb scale, outcome cells, and calendar. This support covers
96.75% of the 2017--2019 construction employment weight.

| model | computer control | family-by-month FE | Q5 by post | occupation SE | occupation 95% interval |
|---|---:|---:|---:|---:|---:|
| baseline | no | no | -0.09575 | 0.04341 | [-0.18068, -0.01081] |
| computer only | yes | no | -0.19660 | 0.06076 | [-0.31606, -0.07714] |
| family only | no | yes | 0.03539 | 0.06214 | [-0.08589, 0.15667] |
| combined | yes | yes | -0.04665 | 0.06921 | [-0.18207, 0.08877] |

The covariance-preserving paired movements are:

| contrast | movement | occupation SE | occupation 95% interval | family-cluster 95% interval |
|---|---:|---:|---:|---:|
| computer only minus baseline | -0.10086 | 0.03842 | [-0.17723, -0.02448] | [-0.17585, -0.02586] |
| family only minus baseline | 0.13114 | 0.04945 | [0.03517, 0.22710] | [0.02430, 0.23797] |
| combined minus computer only | 0.14995 | 0.04541 | [0.06039, 0.23951] | [0.04450, 0.25540] |
| combined minus family only | -0.08204 | 0.03686 | [-0.15461, -0.00947] | [-0.16600, 0.00192] |
| combined minus baseline | 0.04910 | 0.05693 | [-0.06418, 0.16237] | [-0.06414, 0.16233] |

Computer-use conditioning does not explain the negative contrast away. On the
contrary, it makes the Q5 coefficient more negative on identical support. The
family-by-month structure moves it toward zero, and the combined estimate lies
between those two conditional projections. The combined-minus-baseline
interval includes zero. Thus the four cells expose a strong non-additive
interaction between cross-occupation computer conditioning and family-time
absorption; no cell isolates a causal AI channel.

The computer-use-by-post coefficient is positive: 0.04602 per weighted standard
deviation in the pooled computer-only model (occupation interval [0.01171,
0.08032]) and 0.04868 in the combined family-month model (occupation interval
[0.01053, 0.08684]). The construction-weighted standard deviation is 0.97290,
so the corresponding raw O*NET-importance coefficients are 0.04730 and 0.05004
per point. The occupation-score covariance between the computer and Q5
coefficients is -0.000735 in the computer-only model and -0.000655 in the
combined model; family-score covariances are -0.000634 and -0.000498.

The weighted beta/computer correlation is 0.7970. Mean computer use rises from
2.24 in fixed Q1 to 4.35 in fixed Q5. Adding computer use reduces retained Q5
information from 69.1% to 29.0% in the pooled comparison (VIF-like ratio 3.45)
and from 42.5% to 30.0% in the family-month comparison (ratio 3.33). This is a
precision and residual-comparison fact, not a signed mechanism. The observed
negative coefficient movement comes from the fitted joint projection, not from
variance inflation itself.

## Support reconciliation and smaller characteristic block (C01, C06)

The previously competing support counts refer to different rules:

| rule | occupations | construction-weight coverage |
|---|---:|---:|
| maximal computer use | 455 | 96.75% |
| maximal remotability | 408 | 88.58% |
| current six-static-characteristic intersection | 347 | 76.78% |
| historical intersection | 341 | included now-superseded fixed shortfalls |

The current common block holds its 347 occupations and canonical treatment
labels fixed. Its support-only baseline is -0.12372 (SE 0.05140), which must be
shown before any conditioning comparison.

| added dimension | Q5 by post | paired movement from pooled baseline | occupation 95% interval for movement |
|---|---:|---:|---:|
| computer use | -0.24847 | -0.12475 | [-0.20934, -0.04016] |
| remotability | -0.13659 | -0.01287 | [-0.05218, 0.02645] |
| log wage | -0.13540 | -0.01168 | [-0.02935, 0.00599] |
| education requirement | -0.13374 | -0.01002 | [-0.02651, 0.00647] |
| routine-task intensity | -0.11166 | 0.01207 | [-0.02414, 0.04827] |
| manual/physical importance | -0.12223 | 0.00150 | [-0.07929, 0.08228] |
| all six | -0.23331 | -0.10958 | [-0.22069, 0.00152] |
| family-by-month, no characteristics | -0.00348 | 0.12024 | [0.00718, 0.23331] |
| family-by-month plus all six | -0.10506 | -0.10158 versus family | [-0.20057, -0.00258] |

Computer use is the only one-at-a-time static characteristic whose paired
interval excludes zero. The other nondetections do not establish that those
dimensions are irrelevant. The all-characteristic and family comparisons again
show that the projections are not additive. The coefficient remaining after
the horse race is not a “purified AI” coefficient.

## Omitted-confounder sensitivity (C04)

`C04_OMITTED_CONFOUNDER_APPLICABILITY.md` records the formal adjudication. The
Oster, Cinelli--Hazlett, and Diegert--Masten--Poirier calculations checked are
linear-regression sensitivity analyses. Substituting a grouped-binomial
pseudo-R-squared would not implement those methods. No scalar breakdown value
is reported for the nonlinear YAX target, and no arbitrary analogue is used.

A SOC2-by-month common young-relative shock is already in the span of the
family-by-month fixed effects. The unabsorbed concern is an occupation-specific,
time-varying within-family factor correlated with exposure; the data provide no
verified strength restriction for it. Sign sensitivity, paired coefficient
movement, and sensitivity of magnitude are therefore discussed separately.

## Corrected pandemic shortfalls (C05)

The C05 calculation is reported separately in
`../shortfall/I08_C05_SHORTFALL_FINDINGS.md`. On its stricter 363-occupation
support, total-stock shortfall conditioning moves the pooled/family-month
coefficients by +0.00040/-0.00050 and young-relative conditioning by
+0.00114/+0.00613. Generated-input resampling increases the uncertainty of
those movements without changing their point estimates. Household cross-fit
directions are heterogeneous, so the exercise does not remove all common-source
error or regression-to-the-mean concerns.

## Actual industry microcells (C07)

The prior run used 3,127 preperiod-connected occupation-by-industry strata in
13 broad industry groups and the byte-identical 468-occupation canonical
membership. All prior receipt hashes, the 81/81 self-check, current membership
identity, the three model score vectors, and all three paired intervals were
revalidated from public artifacts. No dominant-industry occupation proxy is
used.

| model | Q5 by post | occupation SE | occupation 95% interval |
|---|---:|---:|---:|
| valid-industry occupation-month reference | -0.13221 | 0.04536 | [-0.22117, -0.04325] |
| occupation-industry-cell baseline | -0.13759 | 0.04602 | [-0.22752, -0.04767] |
| industry-cell plus broad-industry post slopes | -0.09868 | 0.04624 | [-0.18798, -0.00938] |

Changing from the valid-industry occupation-month objective to the actual
industry-cell baseline moves the coefficient by -0.00538 (paired interval
[-0.01379, 0.00303]). Adding broad-industry post slopes within the microcell
objective moves it by +0.03891 ([0.00817, 0.06965]); relative to the valid-
industry aggregate reference, the movement is +0.03353 ([0.00127, 0.06579]).
This is a descriptive conditioning sensitivity under a changed cell objective,
not an estimate of a causal industry share.

## Manuscript constraint

The paper may state that computer use and occupational-family time structure
materially change the fitted exposure contrast on fixed support. It may not say
that computerization explains the result away, that the residual is uniquely
AI, or that any conditioning movement identifies a causal share. The central
empirical lesson is that the measured contrast depends strongly and
non-additively on which observed occupational dimension and time structure are
partialled out.
