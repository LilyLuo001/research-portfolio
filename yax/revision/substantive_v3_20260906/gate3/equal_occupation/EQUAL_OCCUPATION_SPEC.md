# Gate 3 equal-occupation objective companion

Status: **post-outcome exploratory; written before this companion run**. The
frozen v1.1 design and confirmatory results are unchanged. No output from the
run specified here has been inspected when this document is committed.

This block resolves L01. It evaluates whether the current Rule-A beta result is
sensitive to the employment-stock information weighting of the primary
grouped-binomial objective. It does not redefine CPS person weights as one.

## 1. Baseline objective

For occupation `o` and observed month `t`, let `Y_ot` and `O_ot` be the CPS
employment stocks for ages 22--25 and 26--65 after aggregation with `WTFINL`,
let `N_ot=Y_ot+O_ot`, and let `s_ot=Y_ot/N_ot`. The current estimator maximizes

```
sum_ot [Y_ot log(p_ot) + O_ot log(1-p_ot)].
```

Thus large employment-stock cells contribute more information. The fixed
support, calendar, beta quintiles, Webb-software control, age groups, post
definition, fixed effects, and coefficient target are unchanged.

## 2. Equal-occupation objective and changed estimand

Let `T_o` be occupation `o`'s number of months with `N_ot>0`. The companion
maximizes the fractional-binomial quasi-objective

```
sum_o sum_{t:N_ot>0} (1/T_o) *
    [s_ot log(p_ot) + (1-s_ot) log(1-p_ot)].
```

Every occupation therefore contributes exactly one unit of total objective
weight, divided equally across its positive-employment months. `WTFINL` remains
load-bearing because it constructs `Y_ot`, `O_ot`, and therefore `s_ot`; it is
not removed from person records.

The changed estimand is the best-fitting young-employment-share log-odds
contrast under a distribution that first samples an occupation uniformly and
then samples one of that occupation's positive-employment months uniformly.
It is not the employment-stock-weighted population association and is reported
only as a companion sensitivity.

## 3. Estimation and inference

Both the baseline stock objective and the equal-occupation objective are fit
under the pooled and SOC2-family-by-month specifications. The target remains
Q5 by post relative to Q1. The full baseline must reproduce the current pooled
coefficient `-0.13210945079219025` and family-month coefficient
`-0.021674952018246537` within `1e-8`.

Inference uses 9,999 common occupation- and SOC2-family-level Rademacher score
multipliers. Each equal-minus-stock comparison differences influence vectors
before applying the common draws. A confidence interval containing zero means
only that the design does not detect a difference; it does not establish
equivalence.

## 4. Required outputs and refusal rules

The run stores all model results, paired differences, objective weights,
complete occupation and family influence vectors, failures, and a sanitized
receipt. It refuses to publish if the protected contract moves, if any
occupation has no positive-employment month, if occupation objective weights
do not each sum to one within `1e-12`, if baseline coefficients do not
reproduce, or if any model fails. No microdata row or identifier is written.
