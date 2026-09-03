# P1 viability and ex-ante power audit

**Frozen audit date:** 2026-09-03
**Decision:** `C. NOT PRACTICALLY VIABLE UNDER THE CURRENT DESIGN`

## Executive answer

P1 is not presently powered for the frozen headline design.  The project has 71
Gate0 PASS conversion events in 47 waves, but only 30 waves produce a positive,
ownership-ready U.S.-common-stock exposure.  More importantly, continuous-dose
information is concentrated: the all-sponsor wave-information ESS is **2.90**
and the exclude-Dimensional ESS is **2.88**, despite 8,801 positive stock-wave
cells and 3,440 unique stocks.

Under the primary outcome-free clustered variance design, the 80% MDE is
**1.508 residual-CAR SD** for all sponsors and **2.334 SD** after excluding
Dimensional, evaluated at a one-SD SUE and 0.5% ownership.  Dimensional-only has
two waves but only one adviser cluster, so a cluster-valid MDE is not estimable.
The frozen 0.5-SD benchmark therefore fails.  Even the deliberately optimistic
iid-only lower bound for exclude-Dimensional has an 80% MDE of approximately
0.506 SD.

Targeted recovery can likely fix the narrow K2 stock-count gate: the simulation
first passes 33 exclude-Dimensional stocks at total exact-date **90**, or about
**16 additional exact dates / 10 additional non-Dimensional waves**.  That does
not rescue headline power.  In the intentionally favorable targeted expansion,
80% power for 0.5 SD first appears only at total exact-date **1,300**, requiring
about **1,226 additional exact dates and 784 additional non-Dimensional waves**.
The 90% target is not reached even at 2,000 exact events; at that ceiling it
already requires more than 1,926 additional exact dates and more than 1,232
additional non-Dimensional waves.  Both are far outside the known 247-member
structural universe and 156 completed conversions.

No earnings outcome, CAR, or treatment coefficient was loaded or inspected.

## 1. True sample size

The relevant levels must not be conflated:

| Level | All | Dimensional-only | Exclude-Dimensional |
|---|---:|---:|---:|
| Raw earnings-event observations | not yet observable | not yet observable | not yet observable |
| Gate0 PASS conversion events | 71 | 5 contributing events | 66 other PASS events |
| Gate0 PASS waves | 47 | 2 Gate0 waves | 45 Gate0 waves |
| Positive ownership-ready waves | 30 | 2 | 29 |
| Gate0 adviser proxies | 34 | 1 | 33 |
| Exposure-contributing adviser proxies | 24 | 1 | 23 |
| Positive stock-wave cells | 8,801 | 3,503 | 5,638 |
| Unique positive stocks | 3,440 | 2,548 | 2,979 |
| Unique stocks at ownership ≥0.5% | 573 | 559 | 21 |
| Equal-wave Kish cell ESS | 204.66 | 2,800.24 | 191.23 |
| Wave-information ESS | 2.90 | 1.09 | 2.88 |
| Sponsor-information ESS | 2.73 | 1.00 | 2.86 |

The all-sponsor and subgroup stock counts overlap and therefore are not
additive.  “Sponsor” here is an unsigned adviser-name proxy; the frozen paper
still requires the PI-signed economic-sponsor crosswalk.

Exposure thresholds are:

| Ownership threshold | All stocks | Dimensional-only | Exclude-Dimensional |
|---|---:|---:|---:|
| positive | 3,440 | 2,548 | 2,979 |
| ≥0.10% | 1,776 | 1,513 | 747 |
| ≥0.25% | 1,165 | 1,041 | 285 |
| ≥0.50% | 573 | 559 | 21 |
| ≥1.00% | 27 | 24 | 4 |

Events per Gate0 PASS wave are highly discrete: 31 waves have one event, 12
have two, one has three, two have four, and one has five.  Among the 30 ready
waves, positive stocks per wave have min/p25/median/p75/max of
1/11/40.5/94.5/2,575 (mean 293.4).  The information ESS is much smaller than
either distribution because exposure magnitude is concentrated.  The five
largest all-sponsor wave information shares are W002 52.0%, W016 24.2%, W004
9.7%, W025 7.2%, and W006 3.2%.

## 2. Why 47 PASS waves become 30 ready waves

Every PASS wave is classified in `p1_wave_coverage_audit.csv`:

| Classification | Waves | Interpretation |
|---|---:|---|
| Fully ownership-ready | 11 | Positive cells and ≥95% candidate-value mapping |
| Partially mapped | 19 | Positive cells but <95% candidate-value mapping |
| Non-common-equity only | 9 | Bond/international portfolios with no eligible candidate U.S. common stock |
| Security-mapping failure | 7 | Candidate rows resolve to foreign/ADR, pooled-fund/cash, or otherwise ineligible securities |
| Missing CRSP denominator | 1 | W047, March 2026; 2026 CRSP daily/name denominator is absent |
| N-PORT holdings issue | 0 | — |
| Corporate-action alignment issue | 0 | — |
| Other | 0 | — |

The 17 zero-cell waves are W005, W008, W010, W012, W015, W019, W020, W022,
W026, W027, W028, W031, W033, W035, W043, W046, and W047.  Sixteen are not
technical losses under the frozen U.S.-common-equity treatment definition.
W047 is technically recoverable with 2026 CRSP, but its three equity positions
sum to only about $2,485 in a bond fund and cannot materially affect the 0.5%
gate.  Improving partial mappings can add cells to already-ready waves; it does
not create the missing independent variation.

## 3. Ex-ante MDE method and results

Let `x = ExposureOwnership / 0.005`, so the reported coefficient is the CAR
change for a one-SD SUE at 0.5% ownership.  Each stock-wave cell receives weight
`1 / (W × n_w)`.  The primary design decomposes a unit-variance, treatment-free
SUE-to-CAR slope error into wave/sponsor/stock/idiosyncratic shares of
30%/25%/20%/25%.  The analytic variance uses the actual exposure distribution,
stock repeats, wave sizes, and adviser concentration.  Critical values use
`min(waves−1, adviser clusters−1)` degrees of freedom.  Sensitivity rows use a
cluster-heavy 40%/30%/20%/10% split and an iid-only optimistic bound.

This is a transparent design-based variance assumption, not a P1 residual
estimate.  An untreated/pre-period earnings panel does not yet exist, and the
audit was prohibited from starting outcome construction.  Therefore absolute
basis-point MDEs are correctly marked `NOT_ESTIMABLE_PRE_OUTCOME_PANEL`.
Standardized MDE is the same across 5m, 15m, 30m, 60m, close, and +1d until
horizon-specific untreated CAR variances are available.

| Sample | Waves / adviser clusters | 80% MDE | 90% MDE | 0.5-SD gate |
|---|---:|---:|---:|---|
| All sponsors | 30 / 24 | 1.508 SD | 1.736 SD | FAIL |
| Dimensional-only | 2 / 1 | not estimable | not estimable | FAIL |
| Exclude-Dimensional | 29 / 23 | 2.334 SD | 2.686 SD | FAIL |

The older T2a calculation assumed iid errors and a synthetic one-anchor-wave
portfolio.  It remains a historical preregistration artifact but is superseded
for viability by this calculation using the observed wave/exposure design.

## 4. Economic meaning

The only numerical beta-scale benchmark already frozen before outcomes is 0.5
residual-CAR SD; 1.0 SD is a large-effect sensitivity.  The plan's five
percentage-point `Speed^h` readability threshold is not a signed beta-scale
decision and remains owner-dependent.  No new threshold was chosen after seeing
results.

Prior research supports the economic question and the short-horizon family but
does not supply a directly portable P1 coefficient scale.  Grégoire and
Martineau study 5–60 minute price discovery and show that quote returns are
needed to measure the speed and magnitude of earnings reactions
([Journal of Accounting Research](https://onlinelibrary.wiley.com/doi/abs/10.1111/1475-679X.12394)).
Huang, O'Hara, and Zhong show that industry ETF inception can reduce PEAD
([Review of Financial Studies](https://academic.oup.com/rfs/article-abstract/34/3/1280/5868422)).
The Fed conversion note studies a related conversion design but does not provide
a portable P1 earnings-response effect size
([Federal Reserve](https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html)).

Current clustered MDEs are roughly 3.0 times the 0.5-SD benchmark for all
sponsors and 4.7 times it excluding Dimensional.  They are not economically
acceptable under the frozen power criterion.

## 5. Expansion scenarios

The simulation adds exact events in empirical wave-size blocks, applies the
observed 71/74 Gate0 yield, and resamples actual wave exposure profiles.  It
retains a finite synthetic stock pool to force overlap.  Conservative expansion
mostly reuses sponsors and stocks; proportional expansion follows the current
mix; targeted expansion deliberately selects the highest-information
non-Dimensional U.S.-equity templates, with a high probability of a new sponsor.
The targeted arm is intentionally favorable and should be read as an upper
bound on acquisition performance.

Selected medians:

| Strategy | Exact events | PASS assumed | Total waves | Ex-Dim ≥0.5% stocks | Ex-Dim MDE80 | K2 |
|---|---:|---:|---:|---:|---:|---|
| Current | 74 | 71 | 47 | 21 | 2.334 | FAIL |
| Conservative | 150 | 144 | about 95 | about 23 | about 2.06 | FAIL |
| Proportional | 150 | 143 | about 95 | about 25 | about 1.94 | FAIL |
| Non-Dim targeted | 90 | 86 | about 57 | about 34 | about 1.61 | PASS |
| Non-Dim targeted | 150 | 145 | about 95 | about 84 | about 1.03 | PASS |

Exact medians, 10th/90th-percentile MDE diagnostics, and all 80/90/100/110/120/
130/140/150 rows are in `p1_power_expansion_scenarios.csv`.  The extended
targeted grid is included solely to locate the theoretical rescue bound; it is
not an attainable acquisition plan.

## 6. Rescue target

Three targets have different answers:

1. **Frozen K2 count:** about 16 additional exact dates producing at least 10
   additional independent non-Dimensional waves, if acquisition is highly
   targeted; first simulated pass is 90 total exact dates.
2. **80% power for a 0.5-SD effect:** about 1,226 additional exact dates and 784
   additional non-Dimensional waves in the favorable targeted simulation; first
   grid pass is 1,300 total exact dates.
3. **90% power for a 0.5-SD effect:** not reached at 2,000 total exact dates;
   the audit establishes lower bounds of more than 1,926 additional exact dates
   and more than 1,232 additional non-Dimensional waves.

The first target is a count repair, not a research-design rescue.  The second
and third are impossible inside the current structural universe.

## 7. The 82 non-exact completed events

The pool contains exactly 14 proposed-day-only, 57 month-only, 9 bounded-window,
and 2 year-only events.  `p1_nonexact_82_priority.csv` ranks all 82 without
pretending unavailable AUM exists.  The score uses non-Dimensional status,
domestic-equity/name-based CRSP-mappability signals, likely new wave, date
precision/bracket, proposed date, and existing SEC evidence.  The file labels
these heuristic fields explicitly; they require verification before promotion.

Upgrading roughly 16 well-targeted events across at least 10 new non-Dimensional
waves could pass K2.  Upgrading all 82 cannot approach the 80% power rescue
target of 1,226 additional exact dates.  The 82-event pool is therefore adequate
for a K2 census check but not for salvaging the frozen headline design.

## 8. External data

Morningstar Direct is the first commercial source to test because it publicly
documents a conversion flag, conversion date, predecessor name, and predecessor
share-class ID.  SEC filing recovery against the ranked 82 is the best
marginal-cost action.  Adviser archives are third.  ETF Global/ICE and generic
fund-reference products should be purchased only after a field-level sample
proves conversion lineage and exact dates; their public descriptions establish
ETF reference/holdings coverage, not the required MF-to-ETF event table.  The
full ranked strategy is in `p1_external_data_acquisition_plan.md`.

## 9. Final decision and workflow state

`C. NOT PRACTICALLY VIABLE UNDER THE CURRENT DESIGN`.

Exposure construction and all outcome/regression work remain paused.  The
classification is driven by independent-wave/sponsor information and clustered
MDE, not by `N=71` alone.  P1 must not be restarted by silently dropping
Dimensional-only, exclude-Dimensional, LOSO, equal-wave weighting, or the fixed
inference structure.  Any future redesign is a separate owner decision and must
be frozen before outcomes.

## Reproducibility

Run:

```bash
python3 p1/viability/audit_viability.py
```

The script reads only the frozen event, Gate0, mapping, and exposure files.
`audit_manifest.json` records input hashes, seed, repetitions, output row counts,
and an empty outcome-input list.
