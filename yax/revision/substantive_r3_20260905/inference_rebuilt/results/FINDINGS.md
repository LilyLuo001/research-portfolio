# Findings: rebuilt-treatment inference addendum

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1.**

The canonical 468-occupation, 113-month rebuilt contract gives a pooled Q5--Q1
coefficient of -0.132109 (occupation-cluster SE 0.045174) and a
SOC2-by-calendar-month conditioned coefficient of -0.021675 (SE
0.071323). The paired conditioned-minus-pooled movement is
0.110434 (SE 0.051894); this is a change in a conditioning
comparison, not an allocated causal composition share.

Under 22-family Webb multipliers, the intervals are [-0.211088, -0.053131]
for the pooled coefficient, [-0.153426, 0.110077] for the conditioned
coefficient, and [0.005876, 0.214993] for the paired movement. The common
family draws preserve the covariance relevant to that paired comparison.

At lag 16, the corrected elapsed-calendar inclusion--exclusion target SE is
0.044491 for the pooled estimate and 0.055221 for the conditioned
estimate. The paired target SE is 0.045005. Across all objects and lags,
0 of 15 full five-parameter covariance matrices are
indefinite. Their target diagonals are retained and labeled, but no PSD
projection or silent eigenvalue clipping is applied.

Normal-theory MDEs are reported as precision descriptions only. A confidence
interval containing zero means that the procedure does not detect a difference;
it does not establish economic equivalence. The broad-family and time-HAC rows
are dependence sensitivities, not CPS design-based survey inference.
