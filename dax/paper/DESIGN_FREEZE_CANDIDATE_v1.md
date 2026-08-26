# CPS young-employment chapter — design-freeze candidate v1

**Prepared:** 2026-08-25

**Status:** `BLOCKED_FAILED_PRIMARY_EXPOSURE_COVERAGE`

**Outcome seal:** no wide-extract outcome estimate may be run from this document.

This candidate corrects the estimating object in `CHAPTER_SCOPE_v1.md` before
the wide CPS extract is available. It is not a preregistration and must not be
tagged as one. The old 2021-11--2026-07 ages-22--25 panel has already existed;
only the new 2017--2026 wide panel remains outcome-sealed.

## 1. Inputs and gates

1. IPUMS extract **9** is the only admissible wide extract. It supersedes
   extract 8. The request contains 114 monthly samples from 2017-01 through
   2026-07 with 2025-10 absent and has submitted-spec SHA-256
   `bd798b9dfe11d00153856be3e05a7c52865a149dcc7405a5cbfd812eb3ca6c3a`.
   It completed and was checksum-verified after this candidate was started;
   the data SHA-256 is
   `3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9`.
   Structural validation passed without reading an outcome field: 9,262,480
   rows, 114 requested sample months, ages 16--75, 39 output columns, and no
   errors. The extract-9 codebook subsequently established that the March
   2017--2021 samples are ASEC rather than monthly-basic samples and do not
   supply `WTFINL`. They are structural gaps, leaving 109 usable basic months
   overall and 66 usable pre-period months. `ASECWT` must never be substituted.
2. The exact submitted request is
   `dax/memo/power_calcs/ipums_ai_telework_extract_v2.json`; the sanitized
   submission receipt is beside it. Extract 8 must never be analyzed.
3. C1 must supply the official-crosswalk exposure panel and pass its coverage
   tests before this document can become `DESIGN_FREEZE_v1.md`.
4. The metadata-only contract
   `dax/memo/power_calcs/cps_recode_contract_v1.json` records exact extract-9
   `EMPSTAT`, `OCC`, `OCC2010`, `CLASSWKR`, `WKSTAT`, `WTFINL`, and age rules.
   It was generated from the DDI and codebook without reading microdata.
5. The unsubmitted corrective request
   `dax/memo/power_calcs/ipums_ai_telework_march_patch_v1.json` asks only for
   `cps2017_03b` through `cps2021_03b`, using the identical 32 variables and
   age restriction. It is prepared, not authorized or submitted.
6. Power uses only 2017-01 through 2022-11 outcomes. Treatment estimates,
   post-2022-11 summaries, and `dax/analysis/outcomes/` remain prohibited.
7. The audited raw-record splitter created a private pre-period source containing
   6,188,956 rows and rejected 3,073,524 later rows. For rejected rows it
   decoded only `YEAR` and `MONTH`; it did not split, decode, print, or write
   protected outcome fields. Its sanitized receipt is
   `dax/memo/power_calcs/ipums_extract9_preperiod_split_receipt_v1.json`.

## 2. What CPS can and cannot test

The ADP result is a firm-payroll-data estimate. Payroll names the source, not
the outcome. The official Stanford Digital Economy Lab publication page,
revised August 12, 2026, reports that the sample runs through June 2026 and
that employment of ages 22--25 in AI-exposed occupations is 19 percent below
the less-exposed-peer counterfactual. The locator is:
<https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/>,
lines/facts 49--52 on the publication page as retrieved 2026-08-25.
Its design has millions of monthly records, a balanced firm panel, positive-
earnings and full-time restrictions, and firm-by-month effects. CPS has none
of those firm controls and much smaller occupation-age cells.

The CPS analogue therefore does **not** confirm or reject the ADP coefficient
as the same estimand. It asks whether nationally representative CPS employment
headcounts contain a young-versus-older, high-versus-low exposure change of a
comparable log magnitude.

## 3. Primary estimand

### Population and cells

- Employed people ages 22--65 in the monthly basic CPS.
- Young group: ages 22--25. Comparison group: ages 26--65.
- Employment is defined from the extract-9 codebook as `EMPSTAT` codes
  `{10, 12}` (at work; has job, not at work). `00`, `01`, `20`--`22`, and
  `30`--`36` are excluded.
- Primary occupation starts from raw `OCC`. For 2017--2019, official Census
  conversion rates probabilistically expand each Census-2010 code into its
  Census-2018 target code(s), splitting the survey weight across routes. From
  2020 onward raw `OCC` is already Census-2018 and is used directly. The same
  target-occupation fixed effect therefore spans the full panel. `OCC2010` is
  a separately labelled sensitivity only.
- Occupation is used only for employed people. The chapter does not assign a
  current occupation to a non-employed person and does not estimate an
  individual employment probability conditional on current occupation.
- Collapse routed `WTFINL` to Census-2018 occupation x age-group x month
  employment headcounts.
  A zero headcount is retained.

### Exposure

- Primary measure: Eloundou GPT-4 beta, model-rated (`dv_rating_beta`), because
  it matches the measure named in the ADP paper. This reason is fixed without
  reference to a CPS outcome.
- After the target-occupation join, derive fixed `dv_rating_beta` quintile cuts using
  pre-period `WTFINL` employment for ages 22--65. Record the exact 20/40/60/80
  cuts and weighting window. Missing or partially covered exposure routes are
  excluded without renormalization; at least 90 percent of eligible employment
  weight must remain. Quintile 1 is the reference and quintile 5 is the
  headline contrast.
- Every other declared exposure measure and crosswalk is reported; none may be
  selected because its estimate is favorable.

### Estimating equation

For occupation `o`, age group `a`, and month `t`, estimate weighted-headcount
PPML:

```text
E[N_oat | .] = exp(
    alpha_oa + delta_ot + lambda_at
    + sum(q=2..5) beta_q * 1{Q_o=q} * Young_a * Post_t
)
```

`alpha_oa` are occupation-by-age-group effects, `delta_ot` are occupation-by-
month effects, and `lambda_at` are age-group-by-month effects. The saturated
effects compare the young/older employment ratio within an occupation-month,
net of national age-specific monthly movements and fixed occupational age
composition. They also make the object distinct from an employment-probability
regression that conditions occupation on the outcome.

The primary coefficient is `beta_5`: the post-period change in log employment
for ages 22--25 relative to ages 26--65 in quintile 5 relative to quintile 1.
Inference clusters by occupation. Two-way occupation and month clustering and
occupation wild-cluster-bootstrap p-values are mandatory robustness rows.

## 4. Timing

- The public ChatGPT release was November 30, 2022. Monthly `Post` therefore
  begins **2022-12**, not 2022-11.
- The event-study reference month is 2022-10. November 2022 is reported as an
  event-transition coefficient rather than silently coded as treated.
- Early post: 2022-12 through 2025-06.
- Extension: 2025-07 through 2026-07, with 2025-10 structurally absent.
- The early/extension specification estimates both coefficients jointly and
  reports a Wald test of equality. Comparing significance stars across two
  separate samples is prohibited.
- The extension changes the conclusion only if (a) the equality test rejects
  at 5 percent and the coefficient difference is at least 0.05 log point, or
  (b) adding the extension changes whether the 95 percent interval excludes
  zero or the authenticated 16 percent benchmark. Both the early-only and
  full-window estimates remain reported.

## 5. Mapping the external magnitude

If older employment is held fixed, a relative young-employment decline `r`
maps to the log young/older headcount contrast `log(1-r)`:

| role | relative decline | log contrast |
|---|---:|---:|
| August 26, 2025 authenticated version sensitivity | 0.13 | -0.139262067 |
| November 13, 2025 authenticated version sensitivity | 0.16 | -0.174353387 |
| **August 12, 2026 authenticated current page** | **0.19** | **-0.210721031** |

The repository's older 13-percent power standard remains a historical,
prospectively chosen calibration for the archived DAX design. It does not
override the latest authenticated 19-percent external comparison for this new
chapter.

## 6. Power and minimum detectable effect

Power is computed before post-period outcomes are opened.

1. Build target-occupation x age-group x month headcounts from the 66 usable monthly-
   basic samples in 2017-01--2022-11. Omit the five ASEC March gaps unless the
   corrective basic-month extract is separately authorized and validated. The
   2017--2019 raw codes are expanded through the frozen official bridge, so all
   66 usable months share the Census-2018 target units used after 2020.
2. Preserve the same occupation support and the planned post-month calendar,
   including the missing 2025-10 month.
3. Construct null pseudo-post panels by rotating whole pre-period calendar-
   month blocks; a donor month is shared by every occupation and age group so
   aggregate shocks and cross-occupation covariance are preserved.
4. Fit the exact PPML equation. With two age groups, conditioning on each
   occupation-month total gives an exactly equivalent grouped-binomial logit
   with occupation and month effects. The committed NumPy engine uses this
   conditional likelihood and weighted fixed-effect absorption. Use
   occupation-level Rademacher wild-cluster
   multipliers on null scores/residual contributions. Do not resample persons
   as if CPS records were independent.
5. Inject `beta_5` on the log mean at a grid containing zero, the three values
   above, and a dense grid around the empirical 80-percent crossing. Refit the
   complete equation on every draw.
6. Use at least 999 draws with seed 20260825. Report rejection probability,
   bias, RMSE, 95-percent interval coverage, the empirical 80-percent MDE, the
   number of occupation clusters, and the effective occupation concentration
   of the Q5-vs-Q1 contrast.

The design is **informative for the external-magnitude question** only if both:

- power to reject zero is at least 0.80 when the true log contrast is
  `-0.210721031`; and
- under a true zero, at least 0.80 of 95-percent intervals exclude
  `-0.210721031`.

The 13-percent and 16-percent prior-version values are sensitivities. A null
estimate after a failed power gate cannot be described as evidence against the
latest ADP magnitude.

## 7. Exposure and crosswalk sensitivity

Every exposure-crosswalk combination uses the same equation and timing.
Report both its maximum available sample and a common-support sample. The
unrepaired exact-code merge is a documented malformed merge, not a competing
scientific crosswalk, but its coefficient may be shown to quantify the bug.

A construction materially changes inference if any predeclared condition
holds:

1. coefficient sign reverses;
2. absolute magnitude changes by at least 50 percent relative to the primary;
3. a paired occupation-cluster bootstrap 95-percent interval for the
   coefficient difference excludes zero; or
4. the 95-percent interval changes whether it excludes zero or the 19-percent
   benchmark.

Coverage, number of occupation clusters, quintile transition matrix, and the
largest contributors to the coefficient difference accompany every contrast.

## 8. Remote work and pre-trends

- Primary remote-work adjustment uses the pre-existing Dingel--Neiman
  occupation measure interacted with `Young x Post` in the same PPML model.
- `TELWRKHR` and `TELWRKPAY` are never person-level regressors for employment.
  They begin in 2022-10 and are observed only for employed people at work.
  Older-worker occupation-month rates may be shown descriptively for the RTO
  period but remain endogenous and are not an identification strategy.
- Event-time leads and the 2017--2019 placebo are reported regardless of sign.
  They diagnose the design; they do not select the estimation window.

## 9. Dallas Fed descriptive-series pipeline check

Dallas Fed Chart 1 already owns the descriptive direction in public CPS data;
it is adjacent to, but not the same as, the primary PPML estimand. Before the
primary estimate is run, reproduce its published series as a pipeline check:

- young ages 20--24 and prime ages 25--55;
- 2024 employment-weighted exposure tertiles;
- each exposure group's employment as a share of its age group's employment;
- 12-month moving averages; and
- no regression inference.

Primary source: Atkinson and Yamco, Dallas Fed, January 6, 2026,
<https://www.dallasfed.org/research/economics/2026/0106>. The downloadable
workbook is
<https://www.dallasfed.org/-/media/documents/research/economics/2026/0106data.xlsx>,
SHA-256
`972bcab87986d08b6b05897a57fcaa4f0bc66964e37171fe06534e61dccf4c1a`.
Sheet `data1`, series `Eai3_ma1`, reports 16.36441 in 2022-11 and 15.53797
in 2025-09, a 0.82644 percentage-point (5.05023 percent relative) decline.

The public page/workbook does not identify the exact score lookup file,
occupation crosswalk, or GPT/human rater variant. Do not tune the chapter
pipeline until these two values match. First implement the documented choices;
if the series does not reproduce within 0.02 percentage point and author code
cannot be located, emit `NEED_HUMAN` and retain the discrepancy. Passing this
check validates age/weight/denominator/smoothing mechanics only; it does not
validate the primary PPML design or establish novelty.

## 10. Empty decision table

| gate | threshold fixed here | result | pass |
|---|---|---|---|
| extract 9 completed, checksummed, structurally valid | exact submitted hash; 9,262,480 rows; 114 requested samples; outcome fields not read | PASS | yes |
| codebook recode contract | exact metadata-derived rules; no microdata read | PASS | yes |
| usable basic-month coverage | 109 overall; 66 pre-period; five ASEC March gaps omitted | PASS_WITH_STRUCTURAL_GAPS | yes |
| outcome-blind pre-period split | 6,188,956 rows retained; 3,073,524 post rows rejected before protected suffix decoding | PASS | yes |
| raw-OCC primary contract | official pre-2020 target bridge + direct post-2020 target code; OCC2010 sensitivity only | PASS_CODE_AND_SYNTHETIC | yes |
| real PPML-equivalent engine | exact conditional grouped-logit; injected -0.20 recovered within 1e-5 | PASS_SYNTHETIC_ONLY | yes |
| C1 exposure coverage | at least 90% of eligible `WTFINL` route mass | 88.7005%; shortfall 1.2995 pp | **no** |
| Dallas Chart 1 pipeline | published endpoints within 0.02 pp, or documented unresolved input | — | — |
| 19% detection power | >= 0.80 | 1.000 on failed-gate available support, protocol seed | conditional pass only |
| 19% exclusion under null | >= 0.80 | 1.000 on failed-gate available support, protocol seed | conditional pass only |
| empirical 80% MDE | report in log points and relative decline | -0.035 log point / 3.439% decline, protocol seed | reported |
| extension equality | p-value plus >=0.05 log-point materiality | — | — |
| crosswalk/exposure sensitivity | §7 rules | — | — |

## 11. Requirements before renaming this file

Do not rename this candidate to `DESIGN_FREEZE_v1.md` and do not create a tag
until C1 passes, exposure-quintile cut points are filled, and the pre-period-
only power receipt is committed. The exact codebook recodes are now recorded,
and the power scaffold passes synthetic-only tests; neither result authorizes
opening post-period outcomes or running real power before C1. Because related
short-panel outcomes and published CPS figures already exist, any eventual tag
must be called a **design freeze**, not a prospective preregistration.

## 12. Failed coverage gate and conditional power diagnostic

The official-crosswalk lookup passed its construction audit, but the frozen
primary coverage rule did not pass. Full-component `dv_rating_beta` routes
retain 88.7004544 percent of eligible pre-period employment weight, below the
90-percent threshold by 1.2995456 percentage points. The failure is preserved;
missing routes are not renormalized, the threshold is not revised, and no
post-period outcome has been opened.

For feasibility only, the registered estimator was run on this available
support: 490 occupation clusters, 66 pre-period months, 43 planned post months,
and an effective Q1-versus-Q5 occupation concentration of 58.4209. Across 999
draws per effect, the 19-percent benchmark had rejection probability 1.000 and,
under a true null, intervals excluded that benchmark with probability 1.000.
The empirical 80-percent crossing was -0.035 log point, a 3.439-percent relative
decline. The null rejection rate was 0.0681 and nominal 95-percent interval
coverage was 0.9319, indicating mild over-rejection that must accompany any
power claim.

These results use the protocol's frozen seed `20260825`, 999 repetitions per
effect, and no post-period outcomes. They pass both conditional power criteria
on the available support. That pass cannot override the failed
exposure-coverage gate and does not authorize the outcome stage.
