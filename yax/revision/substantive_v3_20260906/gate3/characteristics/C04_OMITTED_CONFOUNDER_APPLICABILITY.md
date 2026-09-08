# C04 omitted-confounder sensitivity: applicability ruling

Status: post-outcome methodological adjudication. This document does not alter
the frozen v1.1 estimand and does not report a new causal estimand.

## Ruling

The revision does **not** report an Oster delta, a Cinelli--Hazlett robustness
value, or a Diegert--Masten--Poirier breakdown point for the central YAX
coefficient. Those quantities are not obtained by substituting a likelihood or
pseudo-R-squared into a linear-regression formula. No arbitrary analogue is
manufactured.

The central coefficient is a component of a grouped-binomial fixed-effect
projection with a vector of categorical exposure-by-post interactions. Its
outcome, objective, nuisance projection, generated treatment labels, and
weighting are not the scalar linear-regression setup to which the cited
coefficient-stability formulas apply. A separate linear probability companion
would answer a different level-share projection and would not validate a
sensitivity number for the grouped-binomial coefficient. Because the requested
revision is about the existing coefficient, introducing that companion would
add an estimand without resolving the applicability problem.

This is a negative applicability finding, not evidence that omitted-variable
bias is small.

## Methods checked

- Oster, *Unobservable Selection and Coefficient Stability: Theory and
  Evidence*, Journal of Business & Economic Statistics 37(2), 2019,
  pp. 187--204 ([published article](https://doi.org/10.1080/07350015.2016.1227711)).
  Its coefficient-stability calculation is tied to linear coefficient and
  R-squared movements plus assumptions governing proportional selection and a
  maximum R-squared. YAX has no justified mapping from its nonlinear objective
  to those inputs.
- Diegert, Masten, and Poirier, *Assessing Omitted Variable Bias when the
  Controls are Endogenous*, current working-paper version
  ([arXiv:2206.02303](https://arxiv.org/abs/2206.02303)). Their framework
  explicitly addresses endogenous included controls through a linear
  regression selection-ratio model. It does not make a grouped-binomial
  pseudo-R-squared a valid plug-in input, and the paper warns that generic
  residualization need not preserve the required comparison of selection.
- Cinelli and Hazlett, *Making Sense of Sensitivity: Extending Omitted Variable
  Bias*, JRSS-B 82(1), 2020, pp. 39--67
  ([published article](https://doi.org/10.1111/rssb.12348)). Their reported
  robustness values are developed for linear regression coefficients; the
  article itself identifies extension beyond the linear setting as further
  work.
- Masten and Poirier, *The Effect of Omitted Variables on the Sign of
  Regression Coefficients* ([arXiv:2208.00552](https://arxiv.org/abs/2208.00552)).
  This establishes why sign sensitivity and magnitude sensitivity are not
  interchangeable. Accordingly, the revision does not interpret persistence of
  a negative point estimate as robustness of its magnitude.

## Which omitted dimension remains

A family-common young-relative shock varying at the SOC2-by-month level is in
the span of the family-by-month fixed effects. It is absorbed in the family
models rather than represented by a residual sensitivity parameter. The
remaining concern is a within-family, occupation-specific, time-varying factor
that covaries with the fixed exposure labels and young-relative employment.
The data provide no verified strength restriction or external benchmark for
that latent factor.

Computer use and the other static characteristics can themselves proxy for
multiple channels or lie on adjustment paths that are not causally ordered.
Their inclusion is therefore descriptive conditioning; it does not establish
that the included controls are exogenous, and coefficient movement is not
assigned the sign of omitted-variable bias.

## Evidence used instead

The matched characteristic block reports directly observable quantities on
fixed support: the baseline, computer-only, family-only, and combined
coefficients; paired covariance-preserving movements; the computer coefficient
in standardized and raw units; covariance with the Q5 target; information loss;
and collinearity diagnostics. These answer whether the estimate is sensitive to
the named observed dimensions. They do not bound all unobserved confounding.

The manuscript must state separately:

1. **Sign:** whether each reported interval excludes zero under its stated
   inferential procedure.
2. **Magnitude:** the paired movement and its interval, without treating
   nondetection as equivalence.
3. **Unobserved confounding:** no formal scalar breakdown value is available for
   the declared nonlinear target under a verified set of assumptions.
