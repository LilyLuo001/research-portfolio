# I10 elapsed-calendar HAC validation specification

Status: pre-execution specification. No I10 result had been produced when this
file was written.

## Target and authenticated inputs

I10 retains the two current Gate 2 grouped-binomial logit projections and their
paired movement:

- pooled occupation and calendar-month fixed effects;
- occupation and SOC2-family-by-calendar-month fixed effects; and
- family-month minus pooled for the `Q5_x_post` coefficient.

The aggregate-cell input must have SHA-256
`5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717`.
The certified timing-results checkpoint must have SHA-256
`85c04fe8fd37ca245400a80dfa6458957a86fb0b546b4a7516c594dc3123a403`.
Both coefficients must reproduce the certified Gate 2 results within
`1e-6` before covariance results are emitted.

## Score construction and covariance

For each model, nuisance-adjust the five score columns in the same weighted
fixed-effect space used by the estimator, multiply the residualized score by
the grouped-binomial residual, and premultiply by that model's inverse
information matrix. Stack the two five-column influence arrays before forming
covariance so the off-diagonal cross-model blocks are retained.

For Bartlett bandwidth `L`, compute in identical influence units

\[
  V_L = \frac{G}{G-1}\left[
    \sum_o \Psi_o\Psi_o'
    + \operatorname{HAC}_L\!\left(\sum_o\psi_{ot}\right)
    - \sum_o\operatorname{HAC}_L(\psi_{ot})
  \right],
\]

where `G` is the number of occupations and the one occupation CRV1 factor is
applied after inclusion--exclusion. The HAC contains both positive- and
negative-lag cross-products with Bartlett weight `1-h/(L+1)`.

Use elapsed calendar months, not adjacency in the observed array. Insert
zero-score placeholders for the two absent months, December 2022 and October
2025. Report bandwidths `L = 0, 1, 4, 12, 16`; no bandwidth is selected from
the resulting significance pattern.

## Diagnostics and interpretation

For every bandwidth report the unmodified joint 10-by-10 covariance, its
maximum symmetry gap, scaled numerical rank, positive and negative ranks,
minimum and maximum eigenvalues, and the tolerance used to classify the
spectrum. Do not clip or project the matrix. If a target variance is negative,
report it and leave its standard error and interval undefined.

Report estimates, standard errors, and normal intervals for the pooled target,
family-month target, and covariance-preserving paired movement. These are
same-target HAC sensitivities, not replacements for the separately validated
finite-sample procedures.

The public result may contain only aggregate coefficients, covariance entries,
and diagnostics. It must not contain cell stocks, microdata identifiers,
household routes, or private filesystem paths.
