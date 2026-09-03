# Paired-Difference MDE Scale Note

This note corrects manuscript terminology; it does not alter the frozen
pre-outcome precision artifact.

`yax/power/PAIRED_DIFFERENCE_PRECISION_v2.json` defines

`MDE_Delta,80 = 0.0327215699248238`

on the **Q5-Q1 log-coefficient-difference scale**. It is therefore reported as
approximately **0.0327 log points**. Its exponential relative-magnitude
translation is

`100 * (exp(0.0327215699248238) - 1) = 3.3262807745%`.

The exponential translation describes a multiplicative relative magnitude; it
is not an additive 3.27-percentage-point estimand. The realized paired estimate,
standard error, and interval are correspondingly reported on the log scale:

- beta minus alpha: `-0.03240` log points;
- paired standard error: `0.03697` log points;
- 95% interval: `[-0.10235, 0.03755]` log points.

The interval includes zero, so the design does not detect a difference. Neither
that result nor the ex-ante MDE establishes economic equivalence.
