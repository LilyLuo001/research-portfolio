# CPS longitudinal weight audit

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

The actual extract contains no official longitudinal linking weight for the
intended adjacent-month design.

- `WTFINL` is the final basic-month cross-sectional person weight. It targets a
  monthly population and does not by itself correct selection into successful
  longitudinal linkage.
- `EARNWT` is the outgoing-rotation earnings weight. It is limited to earner
  variables and is not a generic panel/link weight.
- Household/person identifiers and `MISH` establish links but are not weights.

Phase-1 weighted counts use the origin `WTFINL` for incumbent-origin margins
and destination `WTFINL` for entry counts, alongside raw counts. These are
sample-size diagnostics only, not a claim of longitudinal representativeness.
A future design would need to predeclare either an unweighted linked-sample
estimand or origin-weighted estimates with an explicit inverse-link-propensity
or calibration sensitivity based only on pre-transition observables. It must
show unweighted results and linked-versus-unlinked balance. Cross-sectional
weights must not be described as solving longitudinal attrition.
