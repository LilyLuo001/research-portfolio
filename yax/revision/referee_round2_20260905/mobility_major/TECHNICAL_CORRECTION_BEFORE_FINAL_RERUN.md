# Technical correction before the final mobility rerun

> **POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1**

The first computational pilot used the predeclared 50,000 pseudo-units and
five rematches per household-cluster replicate.  Before treating its sampling
diagnostic as final, the existing pseudo-size audit was checked.  At 50,000
units, Hamilton allocation represents only 73.8571% of official switch weight,
versus 98.3052% at the sealed 200,000-unit size.  The pilot's plug-in benchmark
mean was correspondingly 0.211 percentage points above the sealed benchmark.
That support change is too large for an exact-support response to RR2-M8.

The final run therefore retains the same 399 household-cluster multiplier
replicates, seed, statistic, and original no-self repair rule, but uses 200,000
pseudo-units and two rematches per replicate.  The total pseudo-unit work per
replicate falls from 250,000 to 400,000 units; two draws still identify
within-replicate Monte Carlo variance, which is averaged over 399 replicates
before subtraction.  The 999-draw alternative-repair comparison is unchanged.

This correction is based on a support failure visible in the previously
published pseudo-size audit, not on whether the pilot gap was large, small, or
statistically distinguishable.  The original pre-results specification is
preserved unedited; this note records the sole final-run amendment.
