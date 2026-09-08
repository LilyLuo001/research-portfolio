# Gate 3 finite-sample findings (I02--I06)

Status: all eleven declared scenarios completed and passed independent
public-output reconstruction. These results replace, rather than reinterpret,
the historical 199-draw 26.7% and 11.3% rejection figures.

## What the simulations identify

The simulations distinguish the structural exposure input from the two fitted
projection targets. This matters in the empirical structural-null design. With
the structural exposure coefficient set to zero, the calibrated nuisance and
family-composition process produces a pooled pseudo-target of **-0.11035**, a
family-month pseudo-target of **0.000005**, and therefore a paired
family-month-minus-pooled pseudo-target of **0.11035**. Rejection of zero for
the pooled or paired projection in that design is not a size failure: zero is
not the fitted target. It is evidence that the pooled exposure contrast can
arise from broad occupational composition even when the DGP supplies no
structural exposure effect.

Finite-sample estimator bias is small relative to sampling dispersion. In the
empirical observed-effect design, absolute bias is at most 0.00102 log point
across the three targets. The consequential failure is interval calibration,
not coefficient optimization or estimator bias.

## Performance of the article's procedures

In the 799-replication empirical observed-effect design, coverage is:

| target | occupation Rademacher | occupation Webb | family Rademacher | family Webb | cross-fit full-refit oracle |
|---|---:|---:|---:|---:|---:|
| pooled | 0.865 | 0.869 | 0.990 | 0.990 | 0.945 |
| family-month | 0.921 | 0.921 | 0.895 | 0.891 | 0.949 |
| family-month minus pooled | 0.889 | 0.892 | 0.992 | 0.992 | 0.945 |

The multiplier distribution is not the problem: Rademacher and Webb results
are nearly identical at a fixed cluster level. Changing the clustering level
does not deliver one adequate procedure for all three targets. Family
clustering is conservative for the pooled and paired targets, but it
under-covers the family-month coefficient and rests on only 22 clusters with
family-by-month fixed effects nested inside those clusters. Occupation
clustering under-covers all three targets in the empirical design. The
out-of-sample full-refit oracle is near nominal coverage, but it is explicitly
an oracle benchmark rather than an implementable data-analysis interval.

The structural-null empirical design leads to the same conclusion. For the
near-zero family-month projection, occupation Rademacher coverage is 0.916
and family Rademacher coverage is 0.888; the oracle coverage is 0.952. For the
nonzero pooled and paired projection targets, occupation coverage is 0.852
and 0.877, respectively. These are coverage comparisons to their independently
computed pseudo-targets, not mislabeled tests of a structural zero.

The prior adverse DGP was reproduced for every archived successful baseline
draw (195/196/196 across null/local/observed inputs), with maximum coefficient
differences below 1.8e-16. Under its structural-null input, occupation
Rademacher coverage is 0.686 for the pooled projection and 0.775 for the paired
movement; the family alternative reaches only 0.849 and 0.881. The oracle is
between 0.951 and 0.954 across all three targets.

## What drives the failure in the empirical calibration

The factor ablations do not support a universal scale correction. For the
pooled and paired targets, occupation-Rademacher coverage in the empirical
structural-null design is 0.852 and 0.877. Removing the common family shock
raises those rates to 0.995 and 0.977; removing serial persistence while
holding marginal family-shock variance fixed raises them to 0.959 and 0.954.
Replacing the family process with an occupation-level AR(1), the case in which
occupation is the imposed shock unit, produces 0.990 and 0.960. Equalizing
sparsity does not repair coverage (0.835 and 0.859), and equalizing influence
only partly improves it (0.890 and 0.902). Dependence level and persistence,
not merely sparse cells or a particular multiplier law, are therefore central
in this calibrated design.

## Computational resolution

All 11 scenarios stopped under the declared accuracy rule before the 1,999
cap. They used 799 to 1,599 outer replications, 9,999 common multiplier draws
per refit, and had zero failed joint refits. The largest relevant binomial
Monte Carlo standard error is 0.01210, below 0.0125; the largest empirical-SD
relative Monte Carlo error is 0.02761, below 0.05. Separation was retained and
reported, not classified as an unexplained numerical failure.

## Consequence for the paper

No article procedure is validated across the pooled, family-month, and paired
targets in the empirically calibrated DGP. The manuscript therefore cannot
use a significant wild-score interval as a sharp rejection claim or present
the family procedure as a universal repair. The point-estimate decomposition
remains informative: the pooled coefficient is sensitive to broad-family
composition, and the calibrated structural-null DGP reproduces almost exactly
the observed 0.110 movement between pooled and family-month projections. The
revision must present that movement as descriptive evidence about projection
and support, with the finite-sample uncertainty limitation visible.

The simulation does not prove that the empirical null DGP is the true CPS
sampling law. It shows that the article's preferred inference is not reliable
under the empirically calibrated dependence structure and that the available
cluster alternatives do not solve all targets simultaneously. No standard
errors are inflated by an ad hoc factor, and no oracle critical value is
transferred to the data.

## Evidence

- Complete table: `results_20260908/ALL_SIMULATION_SUMMARY.csv`
- Core comparison: `results_20260908/CORE_SIMULATION_COMPARISON.csv`
- Null and factor-ablation comparison:
  `results_20260908/NULL_AND_ABLATION_COMPARISON.csv`
- Independent reconstruction:
  `../../runs/gate3_simulations_adaptive_20260908/INDEPENDENT_VALIDATION.json`
- Scenario receipts and retained replicate results:
  `../../runs/gate3_simulations_adaptive_20260908/`
