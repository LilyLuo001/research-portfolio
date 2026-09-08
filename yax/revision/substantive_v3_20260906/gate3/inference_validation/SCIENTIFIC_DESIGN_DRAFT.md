# Gate 3 inference validation: scientific design draft

Status: **design draft; no Gate 3 result has been produced**

This unit answers I01--I07 and supplies the simulation component of I08. It
does not reinterpret the earlier 199-draw pilot as validation. The pilot is a
historical diagnostic because it used a family-by-post companion rather than
the central family-by-calendar-month model, evaluated normal intervals rather
than the article's wild-score intervals, and did not establish every fitted
model's pseudo-true target.

## 1. Objects and targets

All aggregate simulations use the current 468-occupation corrected-treatment
support, fixed pre-period labels, the corrected 113-month calendar, and the
same grouped-binomial objective as Gate 2. December 2022 is excluded and the
unobserved October 2025 cell is never interpolated.

Every simulated sample is fit with both current central models:

1. the pooled occupation-plus-calendar-month model; and
2. the SOC2-family-by-calendar-month model.

For every refit, iteratively remove fixed-effect groups whose retained outcome
is entirely young or entirely older. Such groups have no finite grouped-logit
fixed-effect maximizer and supply no within-group coefficient information;
removing one group can create another one-sided group in the other fixed-effect
dimension, so removal continues to closure. Report the removed-row fraction
separately for the pooled and family-month estimators. A successfully trimmed
maximum-likelihood fit is not counted as an unexplained optimizer failure.

For each model the reported target is its Q5-by-post projection coefficient.
The third target is the paired family-month-minus-pooled coefficient. Common
simulation innovations and common multiplier draws must preserve covariance.

For every DGP, the three targets are defined by fitting both models to the
analytic DGP mean stocks. They are independently numerically certified before
any rejection or coverage statistic is computed. A structural exposure
parameter of zero is not substituted for a projection target. The analysis
separately reports:

- structural input effect;
- pseudo-true pooled and family-month projection coefficients;
- finite-sample bias relative to each projection target;
- interval coverage of each projection target; and
- zero rejection, which is a size statistic only when that DGP's corresponding
  pseudo-true target is zero to the declared numerical tolerance.

## 2. Declared DGP collection and ablations

The calibration program must record the observed weighted totals, rounded
Kish effective counts, fitted probabilities, score/information concentration,
and family-month residual-shock moments. It must report uncertainty for
estimated calibration moments by a declared family resampling calculation or
leave-one-family range; a point calibration alone is insufficient.

The simulation collection is limited to the following designs. Each changed
design receives newly computed pseudo-true targets.

1. **Empirically calibrated design.** Actual support, totals, Kish counts, and
   fitted nuisance index. Add a common SOC2-family-by-month Gaussian AR(1)
   logit shock whose innovation scale and persistence are estimated from the
   family-month residual series. Report the estimator, weighting, uncertainty,
   and any pooling across families explicitly.
2. **Prior adverse design.** Reproduce the earlier sparse-cell construction
   and complete-path SOC2-family sign shock as exactly as the current contract
   permits. Any unavoidable change from the archived implementation is listed
   field by field.
3. **Sparsity/weight ablation.** Keep the empirically calibrated probability
   process but replace heterogeneous effective counts by one
   variance-preserving common count while retaining cell totals. With
   \(v_c=N_c^2p_c(1-p_c)\), set
   \(n^*=\sum_c v_c/\sum_c(v_c/n_c)\) and round once. This removes count
   heterogeneity without mechanically changing aggregate stock-innovation
   variance at the analytic DGP mean.
4. **Family-dependence ablation.** Keep actual sparse counts and fitted index
   but set the calibrated broad-family shock variance to zero.
5. **Serial-dependence ablation.** Keep the calibrated family-shock variance
   and contemporaneous family sharing but set AR(1) persistence to zero.
6. **Influence-concentration ablation.** Equalize predeclared occupation
   information totals within SOC2 family while preserving the family total,
   calendar, treatment, and probability process. Report the exact rescaling
   rule and recompute all pseudo-true targets.
7. **Occupation-shock design.** Replace the common family shock by independent
   occupation-by-month stationary Gaussian AR(1) paths, holding calibrated
   persistence and marginal variance fixed. This is the design in which the
   article's occupation cluster is the imposed shock unit; a family-shock-only
   collection cannot by itself validate occupation clustering.

The ablations diagnose this finite design; they do not identify a universal
variance correction or the true CPS sampling law.

For Rademacher shock layers, analytic DGP means average the positive and
negative logistic probabilities. When more than one independent binary shock
enters a cell, enumerate all sign combinations for that cell. A Monte Carlo
approximation is not used to define truth when this finite integration is
available.

For the Gaussian calibrated layer, compute marginal mean probabilities by a
fixed high-order Gauss--Hermite quadrature and verify quadrature stability by
doubling its order. Initialize every AR(1) path from its stationary marginal,
\(u_{g1}\sim N(0,\sigma_\varepsilon^2/(1-\rho^2))\), and use the
\(\rho^h\) transition across calendar gaps. The serial-independence ablation
sets \(\rho=0\) while retaining
\(\sigma_u=\sigma_\varepsilon/\sqrt{1-\rho^2}\), so it changes dependence but
not marginal variance or analytic pseudo-truth. The runner verifies constant
theoretical marginal variance and a simulation diagnostic across months.

## 3. Inference procedures compared on every successful refit

Each simulated dataset is fully refit under both central models. For pooled,
family-month, and their paired movement, evaluate:

- occupation-cluster Rademacher wild-score inference using the article's
  fixed-studentizer rule;
- occupation-cluster Webb six-point wild-score inference with the same score
  and fixed studentizer, isolating multiplier choice from cluster level;
- SOC2-family Rademacher wild-score inference with the declared family
  finite-cluster correction;
- SOC2-family Webb six-point wild-score inference with the same score and
  studentizer definition; and
- an out-of-sample finite-sample benchmark obtained from full-refit Monte
  Carlo distributions, clearly labeled an oracle benchmark rather than an
  implementable data-analysis interval.

No normal interval may be described as validation of a wild-score interval.
Occupation and family uncertainty are alternative shock structures and are
not added. Household sampling sensitivity is reported separately and is not
added to either cluster covariance.

Occupation influence uses the active-occupation correction
\(G_o/(G_o-1)\); family influence uses \(22/21\). Every multiplier interval
holds that fitted influence covariance fixed: the multiplier changes the
reference distribution, not the studentizer. The nesting of family-by-month
fixed effects inside 22 family clusters is reported as a limitation of that
alternative procedure rather than hidden.

For the full-refit benchmark, deterministic odd/even replicate streams form
calibration and evaluation halves. Critical values are learned only on the
calibration half from deviations around the known pseudo-true target and are
evaluated only on the other half; the roles are then reversed and the two
evaluation sets pooled. This cross-fit prevents reporting in-sample empirical
coverage of quantiles estimated from the same draws.

## 4. Replications, failures, and Monte Carlo accuracy

Use deterministic common random numbers across the three targets and across
factor ablations wherever their innovation dimensions coincide.

- Pilot: 399 outer replications per DGP and 9,999 multiplier draws from fixed,
  recorded seeds.
- Expansion: add outer replications in blocks of 400, without replacing pilot
  draws, up to 1,999 per DGP.
- Stop only when, for every primary null-target coverage/rejection comparison,
  the binomial Monte Carlo standard error is at most 0.0125 and the approximate
  relative Monte Carlo error of the empirical SD is at most 5 percent. The SD
  error uses the observed fourth central moment,
  \(\sqrt{(\hat\mu_4/\hat\sigma^4-1)/(4n)}\), rather than the normal-theory
  shortcut that is mechanically nonbinding at the 399-draw pilot.
- If the cap is reached first, label that comparison numerically unresolved
  and report its achieved uncertainty. Do not select a procedure by its effect
  on the observed headline.

All attempted fits remain in the denominator. Report convergence,
separation/boundary, and numerical-certificate failures by DGP, model, and
procedure. Coverage conditional on successful fits may be shown only beside
the unconditional attempted-replication accounting. Failed draws are never
silently deleted or replaced.

For each DGP, model, target, and procedure report the pseudo-truth, mean
estimate, bias, empirical SD, mean reported SE where defined, interval length,
coverage, zero-rejection rate, failure rate, and Monte Carlo uncertainty.

`Zero rejection` is called empirical size only when the pseudo-truth is zero
within a numerical tolerance of
\(\max(10^{-10},10^{-6}\times\overline{SE}_{occupation})\). This is a
numerical classification rule, not an economic equivalence region; larger
projection offsets remain confounding or estimand differences.

## 5. Household full-refit sensitivity

The household exercise uses positive `CPSID` multiplier units, gives each unit
one multiplier across all observed months, and gives every fractional route
descendant of a source record that same multiplier. It is not CPS design-based
inference because public strata, PSU, and Basic Monthly replicate weights are
unavailable in the authorized extract.

Every draw must fully refit the pooled and the **same family-by-calendar-month
model** used in the central aggregate analysis. The prior family-by-post
companion does not satisfy I07. Fixed-label and regenerated-preperiod-label
targets are reported separately. Regeneration rebuilds construction weights,
quintile cutoffs/memberships, and Webb normalization; it does not claim
uncertainty in the external exposure lookup.

Start with 399 draws, expand in blocks of 400 to at most 1,999, and stop only
when each reported interval endpoint's bootstrap Monte Carlo standard error is
at most 0.01 log point or the cap is reached. Endpoint error is estimated by a
documented bootstrap-of-bootstrap or density-at-quantile method. Common draws
preserve the paired movement. Results remain separate from occupation/family
shock inference.

## 6. Generated inputs and inference consequences

The regenerated-label household analysis is the feasible full-pipeline
treatment-construction sensitivity. Any pandemic-shortfall generated regressor
requires its own resampling implementation; fixed shortfall values do not
inherit label uncertainty by implication. If its source records or construction
code are unavailable, I08 retains an exact input blocker for that component.

The findings document selects no universal correction factor. If none of the
article's procedures has adequate coverage in the empirically relevant
designs at resolved Monte Carlo precision, the manuscript must demote sharp
rejection language and show the uncertainty limitation. A calibrated or
test-inverted interval may enter only if its construction and out-of-sample
coverage are separately validated.

The historical 26.7% and 11.3% rejection figures are withdrawn as validation
claims. They came from a 199-draw exercise without independently established
pseudo-truths and without the current same-target wild-score comparisons. The
new design may reproduce them only as historical diagnostics and replaces
their inferential interpretation with the Gate 3 results.

## 7. Required mechanical validation

Before a Gate 3 result can be used, an independent validator must recompute:

- all input and output hashes and the exact model/DGP/procedure inventory;
- analytic pseudo-true means and the two certified projection fits;
- common-draw paired covariance identities;
- wild-score statistics and intervals from stored aggregate influence objects;
- cross-fit benchmark split membership and critical values;
- every summary from retained replicate-level aggregate results;
- Monte Carlo stopping criteria and attempted-fit denominators; and
- absence of person, household, cell-stock, or protected path disclosure.

I10 (elapsed-calendar HAC and cross-model covariance) is a separate same-target
module. It must use Gate 2 score objects, include positive-lag within-occupation
overlap subtraction, preserve calendar gaps, and report the unmodified matrix
spectrum; it is not inferred from this simulation.
