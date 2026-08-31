# YAX Future CPS Flow Analysis Plan

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This document specifies a possible next stage. It records no flow coefficient
and authorizes no regression. Because Phase 1 classifies the design as FLOW-B,
the owner must approve and commit a separate flow-analysis freeze before any
outcome below is estimated.

## Feasibility-based restrictions

- Use validated `CPSIDV` and adjacent-month links only: origin MISH
  1/2/3/5/6/7, target month \(t+1\) present, and destination
  MISH = origin MISH + 1.
- Do not pool MISH 4→5 returns after the eight-month absence. Their match rate
  is 73.7% overall and 59.1% for ages 22–25, versus 90.6% and 87.0% for
  adjacent-month links.
- Define age at the origin interview. The audit finds that 1.04% of matched
  adjacent links cross one of the fixed age-bin boundaries.
- Primary age contrast: ages 22–25 versus 26–65, preserving the YAX benchmark.
  Any future six-bin flow profile would require a separate declaration.
- Post begins with January 2023 origins. A December-2022→January-2023 link is a
  transition-boundary observation and is excluded from the static pre/post
  estimands.
- Use Eloundou beta, Rule-A strict exposure and Webb software-patent exposure.
  Form beta quintiles from January 2017–November 2022 ages-22–65 employment
  weights exactly as in V4.1/Phase 1.
- Occupation for an employed respondent means the current occupation in that
  interview. A most-recent occupation reported by a nonemployed respondent is
  never treated as a current origin occupation.
- For a pre-2020 origin or destination, expand the person's transition over the
  existing Census-2010→2018 bridge routes with the published route weights,
  just as stock cells are probabilistically routed. Route weights multiply the
  transition count and sum to one. For transitions requiring both origin and
  destination exposure, use the route-weight cross-product. Preserve raw
  source codes in the audit trail.
- Define an occupational switch using `OCC2010` at both interviews, not a
  change in raw vintage-specific `OCC`. Exclude the 2019-12→2020-01 transition
  from the primary switching outcome because even the modal harmonization
  shows an 11.5% change rate there versus 6.6% elsewhere. Report inclusion of
  that boundary and raw-`OCC` switching only as declared sensitivities.

## Weight and target-population rule

The extract has no official longitudinal link weight. The primary target is
therefore explicitly the population represented by successfully linked
adjacent-month CPS respondents, not the full monthly U.S. population.

For every model report:

1. unweighted linked-sample estimates as primary;
2. origin-`WTFINL` estimates for origin-based margins, and destination-`WTFINL`
   estimates for destination-allocation margins, as sensitivity; and
3. linked-versus-unlinked balance and match rates by age, pre/post, and beta
   quintile.

Neither cross-sectional weight may be described as correcting longitudinal
attrition. A propensity or calibration adjustment is not authorized without a
separate declaration and overlap audit.

## Incumbent origin-based estimands

Let \(R_{oat}\) be linked, employed origins in occupation \(o\), age group
\(a\), and month \(t\). Let \(X^{exit}_{oat}\) count origins nonemployed at
\(t+1\), and let \(X^{switch}_{oat}\) count origins employed in a different
`OCC2010` occupation at \(t+1\).

The exit and switching probabilities are

\[
 p^k_{oat}=E[X^k_{oat}/R_{oat}\mid R_{oat}>0],
 \qquad k\in\{exit,switch\}.
\]

Estimate each margin once as a grouped-binomial quasi-likelihood with
occupation×age, occupation×month, and age×month fixed effects:

\[
 \operatorname{logit}(p^k_{oat})=
 \alpha^k_{oa}+\delta^k_{ot}+\lambda^k_{at}
 +\sum_{q=2}^{5}\beta^k_q Q_{oq}Young_aPost_t
 +\theta^k W_oYoung_aPost_t.
\]

The primary coefficient is \(\beta^k_5\): the post-2022 change for ages 22–25
versus ages 26–65 in Q5 rather than Q1. Treatment is based only on the origin
occupation. Cluster inference by origin Census-2018 occupation; predeclare the
wild-score implementation before execution.

## Entry from nonemployment

Nonemployed origins have no meaningful current occupation, so they receive no
origin AI treatment. Among matched transitions from nonemployment to
employment, construct destination-occupation entry counts \(C^{entry}_{oat}\).
The destination-allocation estimand is

\[
 \beta^{entry}_5:
 \text{the post-2022 change in young-versus-older entry counts into Q5 rather
 than Q1 destinations, conditional on the total age-month entry margin.}
\]

Estimate the same saturated conditional-PPML/count architecture on
destination occupation×age×month entry counts:

\[
 E[C^{entry}_{oat}\mid X]=\exp\left(
 \alpha_{oa}+\delta_{ot}+\lambda_{at}
 +\sum_{q=2}^{5}\beta^{entry}_qQ_{oq}Young_aPost_t
 +\theta^{entry}W_oYoung_aPost_t
 \right).
\]

Here \(o\) is explicitly the destination occupation. The coefficient is a
relative allocation of observed entries, not a probability that a particular
nonemployed person finds work and not an occupation-level treatment assigned
to a nonemployed origin.

## Switch into occupations

Among employed-to-employed transitions that change `OCC2010`, construct
destination-occupation counts \(C^{in}_{oat}\). Estimate the same
destination-allocation model as for entries. \(\beta^{in}_5\) asks whether,
conditional on switching, young workers became less likely after 2022 to move
into Q5 rather than Q1 occupations relative to older workers. It is distinct
from the origin-based probability of switching out.

## Exposure movement among switchers

For switchers define route-weighted

\[
 \Delta AI_i=AI_{destination,i}-AI_{origin,i}.
\]

Report its distribution and estimate one declared linear model with origin
occupation fixed effects, origin-month fixed effects, age-group×month effects,
and the `Young × Post` contrast. This secondary estimand asks whether young
switchers move farther down the beta-exposure distribution after 2022. It is
conditional on switching and is not a causal effect of exposure.

## Required diagnostics before interpretation

- Reproduce adjacent match rates and show the 2.33-point post-2023 decline and
  the age/exposure gradients in linkage.
- Report raw events and risk sets by Q1/Q5, pre/post, and age.
- Show results with and without the 2019/2020 taxonomy-boundary transition.
- Report raw-`OCC`, `OCC2010`, same-major-group, and immediate-reversal
  diagnostics beside any switching estimate.
- Do not use `CLASSWKR` as a same-employer measure; no employer-continuity field
  exists.
- Interpret all coefficients as associations in linked CPS transitions.

No analysis in this document was executed in Phase 1.

