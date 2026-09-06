# Composition and influence analysis specification

**Status:** POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.

This file records the exact composition and influence exercises before their
execution in this revision round.  The protected design and confirmatory
result artifacts are inputs only and must not be changed.

## Common baseline

All exercises begin with the frozen Rule-A Eloundou-beta / Webb-software
Q5--Q1 model: ages 22--25 relative to ages 26--65, frozen employment-weighted
quintile assignments, and the 468-occupation support.  The 108-month frozen
calendar (December 2022, October 2025, and the five misrequested March basic
samples excluded) is retained as the chronology benchmark.  The corrected
113-month calendar restores March 2017--2021 from the authenticated repair
extract and becomes the substantive comparison.  A run is invalid unless it
reproduces the sealed 108-month coefficient `-0.13107397642233506` and the
previously audited corrected-calendar coefficient `-0.1345539535732939`, each
to `1e-10`.

Inference in these new cells uses 9,999 common occupation-level Rademacher
score multipliers.  It remains conditional on the realized weighted CPS cells,
exposure labels, and taxonomy allocation.

## C1. Broad-occupation composition

Two increasingly demanding models will be compared with the baseline on both
the 108-month chronology calendar and the corrected 113-month calendar.

1. Add Census-2018 occupation major-group (SOC2) by post interactions, omitting
   the employment-largest major group because a full set sums to the common
   post indicator absorbed by calendar-month effects.
2. Absorb a separate SOC2-specific young-relative effect in every calendar
   month.  Computationally this is an occupation fixed effect plus SOC2-by-month
   fixed effect grouped-binomial model; the common month effect is nested in the
   latter.  The beta-quintile post interactions and Webb-post term remain.

For each model report the Q5--Q1 coefficient and interval, conditional target
information, effective number of occupation contributors to that information,
top-five information share, information-matrix rank/condition number, and
within-SOC2 quintile support.  Use the common multipliers to report paired
changes from the corresponding calendar baseline.  Failure or singularity
must be reported rather than replaced.  These models change the conditioning
estimand; they are not a formal decomposition of the permutation result and do
not identify an AI effect.

## C2. Quintile profile

Using the frozen baseline fit:

- test `H0: b2=b3=b4=b5` with a three-restriction wild-score Wald statistic;
- assess monotone ordering `0 >= b2 >= b3 >= b4 >= b5` with the least-favorable
  max-t test of the four adjacent differences and simultaneous one-sided upper
  bounds.  Reject monotonicity only if the max-t p-value is below .05; call it
  supported only if all simultaneous upper bounds are at or below zero;
  otherwise label it unresolved.

## C3. Stable-tail comparison

On the literal six-implementation common support, recompute each measure's
employment-weighted quintiles as in the existing tail-stability audit.  Retain
only occupations assigned to Q1 by all six measures or Q5 by all six measures.
Estimate a binary always-Q5 versus always-Q1 post contrast with Webb-post held
in the model.  Report the very limited support and do not generalize beyond it.

## I1. Joint deletion and bounded influence

Authenticate and rank occupations by absolute movement in the frozen LOCO
file.  Holding treatment assignments and regressors fixed, jointly delete the
top 5, 10, and 20 occupations and refit.

Two explicitly data-adaptive robustness diagnostics will also be reported:

- trim the lowest and highest 2.5 percent of signed frozen-LOCO movements
  (12 occupations from each tail, using stable code ordering for ties);
- down-weight rather than delete occupations using
  `w_g=min(1,c/|d_g-median(d)|)`, where `d_g` is the frozen LOCO movement and
  `c` is its 95th-percentile absolute deviation.  The weight multiplies both
  grouped-binomial stocks for every month of occupation `g`.

These are sensitivity diagnostics selected after outcomes were known, not
preferred estimators or robustness proofs.

## I2. Food and in-person service anchors

Use the published occupation taxonomy rather than the approximate IND1990
leisure/hospitality concordance.  With frozen assignments, estimate exclusions
for:

- all SOC major-group 35 food-preparation/service occupations;
- only Q1 occupations in group 35;
- all in-person-service occupations in major groups 35, 37, and 39;
- only Q1 occupations in those three groups.

This is a cleaner occupation-side test of Q1 service recovery, but it does not
remove all post-pandemic shocks and is not an industry-based causal control.
