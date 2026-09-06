# R3 corrected CPS flows and worker outcomes: results summary

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Result in one paragraph

The corrected public-CPS links do not isolate a statistically distinguishable
flow mechanism. The official-weight adjacent-month employment-exit coefficient
is 0.132 log point (occupation wild-score 95% CI −0.042 to 0.307; MDE80 0.254),
while the conditional entry-destination allocation coefficient is −0.070
(−0.250 to 0.110; MDE80 0.260). The analogous twelve-month endpoint estimates
are 0.123 (−0.111 to 0.357) and −0.052 (−0.251 to 0.147). Those signs are
compatible with more exit from, and less entry allocation toward, high-exposure
occupations for young workers, but every official-weight core-flow interval
includes zero and the design cannot assign the stock association to either
margin. Person- and household-score clustering leaves that nondetection intact;
it widens several annual intervals, especially the annual reported-occupation
change result. None of these estimates is an employer hiring rate or a causal AI
effect.

## Compact core-flow table

The coefficient is the post-January-2023 change in the ages 22–25 versus 26–65,
beta-Q5 versus beta-Q1 log rate ratio. Entry destination instead uses a log
allocation ratio conditional on an observed nonemployment-to-employment link.
It is not an employment-finding probability or an employer hiring rate.
Primary intervals use 9,999 occupation wild-score draws. The household interval
is a separate normal conditional-score sensitivity, not a replacement for or
addition to the primary variance.

| endpoint and margin | at-risk origins / observed entries | events | coefficient | primary 95% CI | primary MDE80 | household-score 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| adjacent employment exit | 3,346,227 | 106,968 | 0.132 | [−0.042, 0.307] | 0.254 | [−0.035, 0.300] |
| adjacent reported-occupation change | 3,207,598 | 204,408 | 0.003 | [−0.118, 0.123] | 0.174 | [−0.127, 0.132] |
| adjacent entry destination | 96,981 entries | 96,981 | −0.070 | [−0.250, 0.110] | 0.260 | [−0.232, 0.091] |
| twelve-month employment exit | 1,399,376 | 106,103 | 0.123 | [−0.111, 0.357] | 0.336 | [−0.161, 0.407] |
| twelve-month reported-occupation endpoint change | 1,110,024 | 544,868 | −0.018 | [−0.097, 0.061] | 0.115 | [−0.161, 0.125] |
| twelve-month entry destination | 82,573 entries | 82,573 | −0.052 | [−0.251, 0.147] | 0.282 | [−0.305, 0.201] |

The twelve-month occupation outcome is especially fragile as an economic
switching measure: 49–58% of workers employed at both endpoints have different
detailed `OCC2010` reports, depending on age and period. That can combine real
mobility with reporting/coding inconsistency. The table therefore calls it an
endpoint code change; it is not a count of intervening switches or employers.

## Exit components

Unemployment and NILF events exactly exhaust employment exits in the linked
data. Their coefficients need not add because each is a separate nonlinear
rate-ratio model.

| endpoint | component | events | coefficient | primary 95% CI | MDE80 | household-score 95% CI |
|---|---|---:|---:|---:|---:|---:|
| adjacent | unemployment entry | 32,488 | 0.055 | [−0.272, 0.381] | 0.476 | [−0.264, 0.373] |
| adjacent | labor-force exit | 74,480 | 0.135 | [−0.064, 0.333] | 0.287 | [−0.064, 0.333] |
| twelve-month | unemployment at endpoint | 27,330 | 0.246 | [−0.295, 0.787] | 0.778 | [−0.263, 0.755] |
| twelve-month | NILF at endpoint | 78,773 | 0.078 | [−0.181, 0.337] | 0.365 | [−0.246, 0.402] |

## Link retention is a substantive limit

The validated positive-weight link rate is 90.86% adjacent-month but 68.97%
twelve-month. It is lower for young origins than older origins: 87.17% versus
91.18% adjacent, and 50.98% versus 70.55% annual. It also differs across the
exposure tails: Q1 versus Q5 retention is 89.64% versus 91.78% adjacent and
66.06% versus 71.04% annual. Official longitudinal weights are therefore
essential, but they do not make the linked population identical to the monthly
stock sample. The twelve-month estimates in particular describe a more selected
endpoint population.

This matters empirically. The unweighted adjacent employment-exit coefficient
is 0.200 with a 95% interval [0.058, 0.341], whereas the official-weight result
is 0.132 with an interval containing zero. The same pattern appears for the
labor-force-exit component. The unweighted result is a sensitivity, not the
preferred estimate.

## Worker outcomes

Among workers employed in both adjacent interviews, the young-relative Q5–Q1
change in usual hours is −0.119 hours per week (95% CI −0.295 to 0.057; MDE80
0.255). In the EARNWT-weighted outgoing-rotation sample, the conditional weekly-
earnings coefficient is −0.0245 log point (−0.1024 to 0.0534; MDE80 0.1107), or
−2.42% as a relative conditional-mean comparison. Both condition on employment;
neither is a total labor-input or earnings effect.

Unemployment duration remains descriptive because it is observed only after
selection into unemployment. The weighted mean duration for young observed
employment-to-unemployment links changes from 6.85 to 7.27 weeks adjacent and
from 13.90 to 17.66 weeks at the annual endpoint. These numbers do not identify
an exposure effect on duration.

## Dependence sensitivity

The conditional event-score analysis reproduces all ten coefficients to at most
`8.33e-17` and the saved occupation influences to at most `1.00e-16`. Adjacent
household-cluster SEs are 0.89–1.07 times their occupation-cluster counterparts.
Annual ratios range from 0.93 to 1.78; the largest is the reported-occupation
endpoint change (SE 0.0729 rather than 0.0410). All person- and household-score
intervals include zero. These are one-way, model-based sensitivities conditional
on cell risk sets and event totals. They do not reproduce the CPS sample design
and are not mechanically combined with occupation-shock uncertainty.

## What changed relative to historical Phase 2

Using the corrected March calendar, exact weight patch, stricter validated
links, and the same rebuilt beta/Webb treatment changes the historical adjacent
point estimates as follows. These are implementation comparisons, not paired
tests.

| margin | historical Phase 2 | corrected R3 | change |
|---|---:|---:|---:|
| employment exit | 0.1195 | 0.1325 | +0.0129 |
| reported-occupation outflow | 0.0107 | 0.0025 | −0.0081 |
| entry-destination allocation | −0.0888 | −0.0704 | +0.0184 |

The correction does not reverse the broad qualitative pattern, but it also does
not supply a precise mechanism result.

## Implementation deviation retained, not hidden

The pre-results document internally described the hours outcome in two ways: its
heading and target called for a within-person usual-hours change, while one
paragraph described a conditional mean-hours level ratio. The executed code
uses the former—destination minus origin hours—and reports the coefficient in
hours per week. Because the package is already post-outcome exploratory, this is
recorded as an implementation clarification rather than rewriting the signed
text. No alternative hours result was selected after inspection.

## Bottom line for the manuscript

The useful claim is about inferential resolution: corrected CPS flows do not
pin the stock association on employment exit, destination allocation, or
reported occupational switching. The table can make that imprecision concrete
with risk sets and MDEs. It cannot support statements that the definitions are
equivalent, that AI caused the signs, that employers hired fewer young workers,
or that the displayed margins account for a numerical share of the stock
coefficient.
