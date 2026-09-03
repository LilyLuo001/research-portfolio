# YAX V4.1 Quintile-Weight Audit Summary

## Result in one paragraph

The frozen design is **ambiguous** about the calendar window supplying
employment weights for production exposure quintiles (Verdict 3). The
historical confirmatory implementation used young-plus-older employment stocks
over 108 static estimation months from January 2017 through July 2026,
excluding December 2022 and with October 2025 absent. A single declared
post-outcome sensitivity instead used the 66 available pre-period months from
January 2017 through November 2022 for AI-quintile classification and changed
nothing else. Q5 membership was identical, Q1 Jaccard overlap was 0.970, and 9
of 468 occupations changed quintile. The primary coefficient moved from
-0.13107 to -0.12851, a difference of +0.00257 log points. The pre-period-
weighted estimate has analytic occupation-cluster SE 0.04461, one-step
wild-score 95% CI [-0.21599, -0.04103], and p=.003. This is **W1 — weighting
is immaterial**. The directional and substantive manuscript conclusion does
not change.

## Design verdict

**Verdict 3 — Freeze ambiguity.** The highest-authority sentence says:

> “`Q5–Q1` is defined by employment-weighted exposure quintiles on each
> scenario's estimation support, with tied scores kept together and Q2–Q4
> separately absorbed.”

The freeze does not say which months supply those employment weights. Its power
simulations used only authenticated 2017-01–2022-11 outcomes, and therefore
used pre-period weights, but neither the text nor a pre-outcome test says that
the production estimator must carry those weights forward. Conversely, no
frozen artifact explicitly authorizes using post-period employment stocks in
the classification weights.

This is not exposure-score endogeneity. Eloundou beta is a predetermined,
time-invariant occupational score. The concern is narrower: the historical
category map \(Q_o\) was constructed with weights partly determined by realized
post-treatment employment composition. The audit asks whether replacing those
weights with pre-period employment changes occupational classification or the
reported Q5-versus-Q1 young-relative employment-stock gradient.

## Historical implementation

Production function chain:

1. `run_frozen_v11.py::run` creates `static_months` from every available month
   except the December 2022 transition.
2. `estimate_static` calls `prepare_model` for each measure, support rule, and
   comparison technology.
3. `prepare_model` applies finite exposure/control support first, reads young
   and older stocks on the supplied months, and sets
   `weights=(young+older).sum(axis=1)`.
4. `weighted_quintiles` uses stable mergesort, cumulative weights, left-sided
   20/40/60/80-percent cuts, and left-sided assignment so tied scores remain
   together.

The same helper formed classifications for Table 5A, the native-support Table
5B architectures, and paired Test C. The V4 literal common-support exercise
also used the helper on the fixed 444-occupation intersection. The V4
categorical event study used the historical primary model's static Q1–Q5
classification. Support and weights are therefore measure/support specific;
the algorithm is common.

Historical primary window:

- first month: 2017-01;
- last month: 2026-07;
- included months: 108;
- December 2022: excluded;
- October 2025: absent;
- ages summed for weights: 22–25 and 26–65;
- primary support: 468 occupations;
- post-period employment enters weights: **yes**.

## Primary classification comparison

| Quantity | Full-static weights | Pre-period weights |
|---|---:|---:|
| Q20 cut | 0.162562 | 0.153846 |
| Q40 cut | 0.328947 | 0.324615 |
| Q60 cut | 0.461538 | 0.456522 |
| Q80 cut | 0.537037 | 0.537037 |
| Q1 occupations | 133 | 129 |
| Q2 occupations | 97 | 99 |
| Q3 occupations | 83 | 82 |
| Q4 occupations | 64 | 67 |
| Q5 occupations | 91 | 91 |

Additional comparison:

- Q1 Jaccard: 0.9699;
- Q5 Jaccard: 1.0000;
- occupations changing quintile: 9;
- moving into/out of Q5: 0 / 0;
- moving into/out of Q1: 0 / 4;
- pre-employment-weighted correlation of the two quintile codes: 0.9980;
- raw exposure rank correlation: 1.0000 by construction, because the score did
  not change.

## Primary coefficient comparison

| Weighting rule | Coefficient | Analytic cluster SE | One-step wild-score 95% CI | Wild-score p |
|---|---:|---:|---:|---:|
| Historical 108-month static weights | -0.13107 | 0.04441 | [-0.21704, -0.04511] | .003 |
| Pre-period-only classification weights | -0.12851 | 0.04461 | [-0.21599, -0.04103] | .003 |

\[
\Delta_w=\hat\beta_{preweight}-\hat\beta_{fullweight}=0.00257.
\]

The pre-period-weighted exponential translation is -12.06%. Precisely: the
young employment stock evolved 12.06% less favorably relative to the older-
worker stock in Q5 than in Q1 over January 2023–July 2026. The corresponding
historical translation is -12.28%.

## Six-measure literal-common-support extension

The extension was computationally trivial and used the unchanged V4
444-occupation intersection. All six pre-period-weighted coefficients remain
negative. Coefficient changes range from 0.00000 to 0.00630 log points in
absolute value. Q5 Jaccard overlap ranges from 0.976 to 1.000; Q1 overlap ranges
from 0.969 to 1.000. Five intervals exclude zero. As in V4, the AIOE
administrative-equal interval narrowly includes zero (pre-weight p=.056).

## Decision and manuscript consequence

**State W1 — weighting is immaterial.** The weighting window is a real but
previously underspecified measurement-architecture choice. In this application
it barely changes treatment membership and does not materially drive the
headline coefficient.

The immutable confirmatory estimate is not replaced. The manuscript should
disclose both the historical implemented window and the freeze ambiguity, then
report the pre-period-weighted result as a post-outcome supplementary
sensitivity. It may state that the same directional conclusion survives. It
must not claim that either temporal weighting rule was uniquely pre-specified.

No categorical event-study rerun is needed: primary Q5 membership is identical,
Q1 membership is nearly identical, and the coefficient changes by only 0.00257
log points. The V4 categorical result remains unchanged.

## Scope and integrity

No flow outcome, alternative pre-period, treatment date, support definition,
computerization control, age band, estimator, inference procedure, dynamic
model, or mechanism extension was run. The confirmatory result JSON and ledger
remain unmodified.

