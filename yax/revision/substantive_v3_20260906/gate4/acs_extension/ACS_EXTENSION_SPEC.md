# Gate 4 annual ACS extension specification

Status: **post-outcome exploratory; written before ACS outcomes are read**.
Requirements: B05 and B06. The frozen v1.1 CPS design and its confirmatory
results are unchanged.

## 1. Purpose and reproducibility boundary

The extension answers two separate questions:

1. Does an independently reconstructed public-ACS analogue reproduce the
   direction and sampling precision of Brynjolfsson--Chandar--Chen (BCC)
   Appendix Table H.1?
2. Does the larger ACS sample provide informative within-SOC2-family evidence
   for YAX's distinct young-versus-older employment-stock estimand?

BCC's complete occupation universe, occupation-to-quintile membership and tie
implementation are not public in the artifacts verified by YAX. No output is
called an exact BCC replication. The benchmark is instead reconstructed from
the same published ingredients that are observable: employed persons aged
22--25, GPT-4 beta exposure, occupation-equal quintiles, annual 2022 and 2024
employment stocks, person weights, and the Q5-minus-Q1 difference in growth
factors.

## 2. Files, years and variables

Use the national ACS one-year person PUMS files for 2017, 2018, 2019, 2021,
2022, 2023 and 2024. Standard 2020 one-year data were not released and the
experimental 2020 product is not spliced into the series. As verified on
2026-09-08, 2024 remains the latest released one-year PUMS; no five-year file
may substitute for a missing annual file.

Required person fields are `AGEP`, `ESR`, `OCCP`, `COW`, `WKHP`, the type-of-
unit field (`TYPE` in 2017--2019 and `TYPEHUGQ` from 2021), `PWGTP`, and
`PWGTP1` through `PWGTP80`. Each input ZIP is hashed.
The output receipt records URLs, byte sizes, ZIP member names, uncompressed
sizes, and ZIP-directory CRC32 values. No household or person identifier is
read.

The 2017 Census-2010 occupation codes are fractionally routed through the
authenticated official Census-2010-to-Census-2018 bridge. Codes from 2018
forward are Census-2018 codes and are used directly. Every descendant of one
2017 record carries the same full and replicate weights multiplied by its
official route share. No surviving partial route is renormalized.

Group-quarters persons remain in the all-employed benchmark, matching the
national ACS person universe. A household-only sensitivity using
`TYPEHUGQ == 1` quantifies their contribution.

## 3. Employment populations

Rows are restricted to ages 22--65 with positive person weight and employment
status `ESR` 1, 2, 4 or 5. The benchmark then applies BCC Appendix Table H.1's
reported sequence:

1. `all_employed`: ESR 1, 2, 4 or 5;
2. `civilian_employed`: ESR 1 or 2;
3. `civilian_no_unpaid_family`: prior row and COW not 8;
4. `civilian_wage_salary`: prior row and COW 1 through 5;
5. `full_time_civilian_wage_salary`: prior row and WKHP at least 35.

`all_employed_household_only` is reported separately and is not part of the
sequential BCC comparison. The primary benchmark age group is 22--25. The
YAX extension defines young as 22--25 and older as 26--65.

## 4. Exposure definitions and support

Three definitions are reported without selecting among them after results:

- `BCC_analogue_primary_equal`: occupation-equal, tie-preserving quintiles
  recomputed from raw Rule-A beta on the fixed 468-occupation YAX support;
- `YAX_primary_fixed`: the frozen employment-weighted YAX membership on those
  same 468 occupations; and
- `BCC_analogue_broader_equal`: occupation-equal, tie-preserving quintiles on
  the 490-occupation beta-valid broader support that does not require Webb.

The first and third isolate the effect of admitting the 22 beta-valid
occupations while retaining BCC's published occupation-equal construction.
The first and second isolate grouping construction on the same support.
Assignments are external and fixed in all 80 replicate-weight calculations;
survey reweighting never silently rebuilds exposure groups.

Support and information are separate outputs. For each definition, population,
year, age group and quintile report occupation count, weighted stock,
respondent-equivalent count, and effective sample size. Report the direct
Q1--Q5 family graph and preperiod-stock shares separately; a larger respondent
sample is not described as creating missing occupation-by-exposure support.

## 5. BCC public-ACS analogue

For each sequential population and exposure definition, let

`g_q = employment_stock(q, 2024) / employment_stock(q, 2022)`.

The benchmark is `g_5 - g_1`. The unweighted respondent-count analogue is
reported separately. There is no log transformation. Published BCC values are
comparison targets only: -0.022 for all employed and -0.019 for full-time
civilian wage-and-salary workers. A difference from these values may reflect
the unavailable membership, not a failure of ACS arithmetic.

For each endpoint year, recompute the entire nonlinear statistic with each of
its 80 person replicate weights while holding the other year at its full
weight. With the two annual samples treated as independent address samples,
the design variance is the sum of the two year-specific SDR components:

`Var(theta) = sum_y (4/80) * sum_r (theta[y,r] - theta_full)^2`.

The receipt records the assumption and the official SDR factor. Paired
differences across populations or exposure definitions use the same perturbed
year and replicate index before differencing.

## 6. Annual YAX young-relative extension

Exclude 2020 and treat 2022 as an explicit transition year. The estimation
calendar is 2017, 2018, 2019 and 2021 as pre; 2023 and 2024 as post. For
`YAX_primary_fixed` and `BCC_analogue_broader_equal`, and for all-employed and
full-time civilian wage-and-salary populations, estimate the same grouped-
binomial conditional-Poisson objective as YAX under:

- occupation plus year fixed effects (`pooled`); and
- occupation plus SOC2-family-by-year fixed effects (`family_year`).

The target is the Q5-by-post coefficient relative to Q1. Exposure labels and
base-weight support are common across structures and held fixed in all
replicates. Any fit that drops separated cells or fixed-effect groups is
refused rather than silently changing the paired estimating rows. Report
occupation-shock Rademacher and family-shock six-point Webb multiplier
intervals separately from ACS sampling intervals.

For ACS sampling variance, replace one year's full-weight cells with one
replicate-weight set, refit, and sum the six year-specific SDR components.
Paired pooled-minus-family-year uncertainty differences before squaring, so
covariance is retained. Because addresses can re-enter the frame after five
years and PUMS identifiers cannot link them across years, this block-independent
panel variance is an approximation. Repeat the model on the non-reuse calendar
2017, 2021, 2023 and 2024; do not call either construction exact multi-year ACS
design-based inference.

## 7. Refusal and interpretation rules

The runner refuses publication if a ZIP/member hash changes during use; a
required field or replicate is missing; occupation vintage is ambiguous; the
bridge loses source mass; support or labels drift across paired models; a
quintile disappears; a fit fails; a replicate estimate is missing; or a
reported SDR quantity cannot be recomputed.

The extension remains descriptive. More precise ACS sampling intervals do not
identify an AI effect, and family-year conditioning does not create exposure
support. An interval containing zero means only that the design does not detect
a difference; it never establishes equivalence.
