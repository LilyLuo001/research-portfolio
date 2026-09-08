# D05--D07 age-composition and enrollment specification

Status: post-outcome, referee-led V3 specification. This file is fixed before
the D05--D07 extension is estimated. The exercise is descriptive and does not
turn any older group into an untreated counterfactual.

## Shared contract

Use the current 468-occupation Rule-A beta membership, fixed preperiod
quintiles, fixed Webb-software normalization, and the corrected 113-month
calendar. Replace the wide-file March 2017--2021 ASEC samples with the separately
authenticated Basic Monthly repair before filtering. Omit December 2022 and do
not create October 2025. Route pre-2020 employed occupation records through the
authenticated Census-2010-to-2018 bridge; retain its fractional weights.

All regressions are the current grouped-binomial young-relative weighted-stock
criterion, estimated both pooled and with SOC2-by-month effects. Report
occupation-cluster and SOC2-family-cluster uncertainty and covariance-preserving
paired differences from 9,999 common Rademacher draws. A confidence interval
containing zero means only that the design does not detect a difference.

## D05: older comparison groups

Use young ages 22--25 and compare them with five older denominators:

1. ages 26--65 (the current comparator);
2. ages 26--30;
3. ages 31--40;
4. ages 41--50;
5. ages 51--65.

Estimate all five on one support selected before the postperiod: an occupation
must have positive January 2017--November 2022 young stock and positive stock in
each of the four disjoint older bands. No postperiod count threshold is used.
The four bands and the full comparator share exactly the same occupations,
labels, Webb scale, months, objective, and multiplier draws.

Also construct a fixed-age-composition ages-26--65 denominator. Let
`P_at` be the national WTFINL-weighted Basic Monthly population at exact age
`a` in observed month `t`, `P_t=sum_a P_at`, and

`pi_a = sum_{t in pre} P_at / sum_{t in pre} P_t`.

Each employed age-`a` stock in month `t` receives factor
`P_t*pi_a/P_at`. Thus the standardized older stock is the employment stock that
would prevail at the month-specific size of the ages-26--65 population if its
exact-age shares were fixed to their aggregate preperiod values. This changes
the denominator construction, not the exposure treatment. Validate positive
population denominators and that `sum_a P_at*(P_t*pi_a/P_at)=P_t` every month.

## D06: enrollment restrictions

Audit observed `SCHLCOLL` codes in the actual wide and March-repair files after
the replacement rule. Codes 1--4 are enrolled, code 5 is not enrolled, and all
other codes are invalid/not in universe for the restriction. Never classify an
invalid code as nonenrolled. The observed valid enrollment universe is ages
16--54; ages 55--65 are therefore never included in a claimed common-observable
nonenrollment comparison.

Estimate two paired collections:

- nonenrolled young ages 22--25 versus all employed older ages 26--65, compared
  with unrestricted young ages 22--25 versus the same all-older denominator;
- nonenrolled young ages 22--25 versus nonenrolled older ages 26--54, compared
  with unrestricted young ages 22--25 versus unrestricted older ages 26--54.

Each pair uses one preperiod common support requiring positive numerator and
denominator stock for both pair members. These are selected-population
descriptions: current enrollment may respond to labor-market conditions.

## D07: composition outputs

Report education, enrollment, exact-age, and approximate `YEAR-AGE` profiles by
year and pre/post period among employed young people whose occupation is on the
fixed support. Separately report national ages-22--25 population profiles using
all positive-weight person records. The national profile may use employment and
education/enrollment status, but it receives no occupational exposure value or
quintile. No age-period-cohort coefficient is estimated.

## Outputs and stop rules

The SCC run may publish only aggregate tables, model/influence summaries, a
failure record, and a hash-bound receipt. It must not publish person or
household identifiers. Stop on input-hash mismatch, failure to reproduce the
protected current young/older cells, invalid enrollment coding, nonpositive
population denominators, failure of age standardization, missing quintiles, or
an uncertified grouped-binomial fit. A failed model is not silently replaced.
