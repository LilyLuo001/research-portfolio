# Major mobility findings for RR1-M11 and RR2-M8

> **POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1**

## Bottom line

The revision changes the interpretation of the mobility evidence in three
ways.  First, the six-way 53.28% conflict rate is not a typical pairwise
disagreement rate: an explicitly family-balanced average is 20.13%.  Second,
the no-self benchmark excess remains about 0.96 percentage points on exactly
matched support, but its sampling uncertainty is roughly two orders of
magnitude larger than the Monte Carlo standard error previously emphasized.
Third, the available entry result is an imprecise destination-allocation
contrast conditional on entering employment; it is not a hiring or
employment-finding probability.

These findings support retaining mobility as a measurement diagnostic, not as
evidence about an aggregate hiring mechanism or as a validated correction for
occupation miscoding.

## 1. Family-balanced pairwise disagreement

On all 108,500 six-way-common-support switches, official-weight
zero-threshold pairwise conflict averages:

| conceptual comparison | average conflict among all switches |
|---|---:|
| within AIOE (3 pairs) | 7.56% |
| within task shares (3 pairs) | 23.18% |
| between families (9 pairs) | 29.64% |
| **equal one-third weight to each block** | **20.13%** |

Conditional on both pair movements being nonzero, the family-balanced rate is
20.49%.  Results on the hard-benchmark represented support are effectively
the same (20.13% and 20.50%).  The full pairwise matrix is in
`results/FAMILY_BALANCED_PAIRWISE_DISAGREEMENT.csv`.

The normalization is deliberately transparent: it gives one third to each of
within-AIOE, within-task-share, and between-family comparisons.  It prevents
the nine between-family pairs from receiving three times the weight of either
three-pair within-family block.  It is a descriptive summary, not a unique
economic-loss function.  Consequently, the manuscript should not lead with
53.28% as though it were the disagreement probability for two representative
architectures.

## 2. Beta is redundant for endpoint directional conflict

The occupation scores verify to numerical precision that

`beta = (alpha + broad) / 2`.

The maximum absolute occupation-level identity discrepancy is
`7.0e-13`.  For a switch, beta's raw movement is therefore the midpoint of
the alpha and broad movements.  If both endpoints have the same strict sign,
their midpoint has that sign; dividing each measure by a positive standard
deviation preserves it.  Across 66,582 switches with same-sign endpoints,
there are zero beta sign violations and zero cases in which beta creates a
new endpoint conflict.  Beta can still affect separately standardized
magnitude thresholds or movement-mass statistics.  It does not add a third
independent vote to zero-threshold task-family directional conflict.

## 3. Exact support reconciliation and omitted-support bounds

Hamilton allocation represents 84,192 of 94,893 detailed transition cells,
97,759 of 108,500 source switch rows, and 98.3052% of official switch weight.
The earlier comparison mixed the all-support realized rate with a benchmark
defined on this represented pseudo-population.  Exact alignment gives:

| quantity | rate |
|---|---:|
| realized conflict, all switch support | 53.2828% |
| realized conflict, represented support | 53.2819% |
| sealed no-self benchmark, represented support | 52.3227% |
| **represented-support realized minus benchmark** | **0.9592 pp** |

The correction is numerically tiny because observed conflict on omitted cells
is 53.3367%, close to the represented rate.  That empirical similarity is not
assumed in the bound.  If the omitted 1.6948% of benchmark support is allowed
any conflict rate in `[0,1]`, the all-support benchmark lies in
`[51.4359%, 53.1307%]`, and the all-support realized-minus-benchmark gap lies
in `[0.1521 pp, 1.8469 pp]`.  The bound retains a positive gap but does not pin
its economic magnitude near one percentage point.

## 4. Sampling uncertainty is not Monte Carlo uncertainty

The sealed 999-rematch benchmark has an across-rematch SD of 0.0544
percentage points and a Monte Carlo SE of its mean of only 0.00172 percentage
points.  That is numerical integration uncertainty conditional on the
observed data.

The new empirical uncertainty diagnostic uses 399 mean-one exponential
multiplier replicates over 74,671 longitudinal household (`CPSID`) clusters,
retaining official `LNKFW1MWT`.  After a documented pilot support failure at
50,000 units, each final replicate rebuilds a 200,000-unit plug-in benchmark
and averages two no-self rematches.  It produces:

| statistic | point | declared cluster SE | 95% interval |
|---|---:|---:|---:|
| represented realized conflict | 53.2819% | 0.1979 pp | [52.8947%, 53.6591%] percentile |
| realized minus benchmark | 0.9592 pp | 0.0776 pp | [0.8070 pp, 1.1113 pp] normal, MC-variance subtracted |

The gap's raw cluster-plus-simulation SE is 0.0857 pp.  Subtracting the mean
within-replicate simulation variance of the two-draw mean yields the 0.0776
pp sampling diagnostic.  The bootstrap plug-in benchmark averages 52.4391%,
versus 52.3227% in the sealed benchmark; the interval is therefore centered
on the sealed aligned-support point and uses the bootstrap for variance rather
than level.  The raw uncentered percentile interval remains in the
machine-readable receipt.

This is a declared household-cluster empirical bootstrap, not CPS
replicate-weight or full complex-survey inference.  It also does not resample
the exposure construction, taxonomy bridge, or latent occupation labels.
Still, it supplies the missing apples-to-apples distinction: sampling
uncertainty in the gap is about 45 times the sealed Monte Carlo SE of the
benchmark mean.

## 5. The rematching distribution is algorithm-defined

The sealed rule first permutes destinations uniformly within each age x month
x broad-origin x broad-destination stratum.  It then scans the first
self-match, selects a feasible swap partner uniformly, and restarts with a
fresh permutation after an impasse.  This preserves detailed margins and
removes every self transition, but it is not uniform over feasible
derangements: different assignments have different numbers of initial
permutations and repair paths leading to them.

The prespecified alternative chooses the bad self-match uniformly before
choosing a feasible partner uniformly.  On the same 200,000-unit
pseudo-population and 999 draws:

| repair rule | benchmark mean | Monte Carlo SE |
|---|---:|---:|
| sealed first-bad rule | 52.32267% | 0.00172 pp |
| alternative random-bad rule | 52.32110% | 0.00170 pp |

The alternative-minus-sealed difference is -0.00157 percentage points.
Margins and zero surviving self-transitions were explicitly checked.  The
result is stable to this one valid repair change, but neither algorithm is a
canonical random-matching distribution.  The appropriate language is
"relative to the specified broad-assortative no-self benchmark," not that
broad assortativity causally explains the realized conflict rate.

## 6. Entry is present, but it is conditional allocation

The earlier Phase-2 flow program already contains 88,535 linked transitions
from nonemployment to employment (12,461 young; 28,319 post-period).  For the
official-weight beta Q5-versus-Q1 destination contrast, the young-relative
post coefficient is -0.0888 log points (about -8.49%), with analytic cluster
SE 0.0976, wild-score 95% CI `[-0.2787, 0.1011]`, and `p = .383`.

This estimand conditions on a linked nonemployed origin becoming employed and
asks where observed entrants are allocated.  It is not an
employment-finding probability or hiring hazard because nonentrants are not
in the destination-allocation likelihood.  Its interval is wide and neither
establishes nor rules out an entry-allocation mechanism.  The employed-to-
employed switch frame remains even farther from the hiring margin.

## 7. Immediate reversals are not a measured error rate

The referee's 9.865% figure comes from the earlier, unrestricted Phase-1
feasibility universe: 11,121 immediate A-B-A reversals among 112,736 observable
first switches for ages 18--65.  In the narrower ages-22--65, six-architecture
common-support frame used here, there are 6,187 reversals among 59,858 switches
with an observable third interview: 10.336% raw and 10.663% under official
weights.  Reversals are 5.948% of official weight over all 108,500 switches,
including those without an observable third interview.  These denominator
differences are now explicit.  An A-B-A sequence can reflect a real temporary
move, a within-job assignment change, proxy reporting, or coding/reporting
error.  It does not reveal a latent true occupation or an occupation-to-
occupation error matrix for the employment-stock panel.

For that reason, no misclassification correction or attenuation curve is
adopted.  In a five-category tail design, unknown differential error can
attenuate, amplify, or reassign the Q5-Q1 contrast.  Treating 9.865% as a
symmetric random error probability would manufacture the requested
correction.  A defensible curve requires a reinterview/validation sample or
audited repeated codes that identify the latent-code transition matrix by
occupation and period.

## Recommended manuscript changes

1. Replace the six-way conflict headline with the full pairwise matrix and the
   20.13% family-balanced summary; retain 53.28% only as the probability that
   at least one of six dependent implementations opposes another.
2. State and prove the beta endpoint redundancy before reporting the task-
   family pairwise rows.
3. Use the 0.9592 pp aligned-support benchmark gap and report the
   `[0.1521, 1.8469]` pp omitted-support bound.
4. Put the 0.1979 pp realized-rate SE and 0.0776 pp gap SE beside the 0.00172 pp
   Monte Carlo SE, labeling each uncertainty source.
5. Describe the no-self reference as algorithm-defined and cite the
   alternative-rule sensitivity.
6. Report entry destination only in the flow appendix, with "conditional on
   entering employment" in the table title and note.
7. Delete any statement that 9.865% is an observed occupation-coding-error
   rate or justifies an attenuation correction.

## Reproducibility

The pre-results specification, SCC executor, aggregate draw files, input and
output hashes, and executable self-check are all in this directory.  The
self-check passes.  Private CPS microdata and identifiers remain outside git;
no respondent or household identifier is present in an output.
