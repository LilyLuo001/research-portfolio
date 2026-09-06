# Definitions-and-corrections addendum

Companion to `REPORT.md`. Every number here is copied from a saved stage log or
read back out of an `out/*.parquet` on SCC. Nothing is recomputed and nothing is
reconstructed from memory. Where a digit was not recoverable it is marked
`NOT RECOVERED` rather than guessed.

Two things this addendum does **not** do: it does not change any numerical
result, and it does not soften a finding. It restores figures that were clipped
in the terminal transcript, reconciles counts that legitimately differ, corrects
two transcription errors, and narrows seven interpretive claims that were
stated more broadly than the evidence supports.

---

## 1. What each displayed result actually is

`freq`/`kind` refer to filter values inside `s3_delay.parquet`. "Block CI" means
a 1,000-draw bootstrap that resamples **whole calendar dates**, jointly across
the three ETFs, so a source event replicated into several ETF rows is never
counted as several shocks.

| # | result — source output | outcome variable and units | regressor / surprise definition | sample and formation | N | reaction-date mapping | dependence method | uncertainty as reported |
|---|---|---|---|---|---|---|---|---|
| 1 | Weekly D1, source stocks — `s3_delay.parquet` (`freq=weekly, kind=stock`) | `D1 = 1 − R²(contemp)/R²(contemp+4 lags)`, unitless ratio of raw R² | CRSP value-weighted `vwretd`, contemporaneous plus 4 weekly lags, identical rows both models | Wed-to-Wed weekly returns, ~52 weeks ending at each 30 June formation, 2019–2023 | 2,853 regressions, 596 securities, 5 formation dates, median 52 rows, minimum 40 enforced | n/a — not an event study | none pooled; the cross-sectional distribution is reported, not a pooled standard error | p10 0.0297, p25 0.0571, **p50 0.1192**, p75 0.2518, p90 0.4870; mean 0.1996, sd 0.2170; joint 4-lag test rejected at 5% in 15.0% |
| 2 | Weekly D1, ETFs (declared adaptation) — same table, `kind=etf` | same | same | same formations, SPY/XLK/XLF only | 15 regressions, 3 securities | n/a | none pooled | p10 0.0012, p25 0.0025, **p50 0.0058**, p75 0.0098, p90 0.0168; mean 0.0070, sd 0.0061; joint test rejected 6.7% |
| 3 | Daily D1 sensitivity (fixed frequency, not selected for significance) — `freq=daily` | same | `vwretd`, contemporaneous plus 4 **daily** lags | 252 trading days per formation | stocks 2,901 regressions / 607 securities; ETFs 15 / 3 | n/a | none pooled | stocks **p50 0.0378**, mean 0.0742, sd 0.1169, joint rejected 21.6%; ETFs **p50 0.0029**, mean 0.0037, sd 0.0036, joint rejected 33.3% |
| 4 | Source-stock response, OLS slope — `s3_response.parquet` | CAR(0,h) of the announcing stock, **bps** | signed surprise = (actual EPS − latest pre-release consensus) as **% of pre-event price**, the close 5 trading days before release; scale fixed before any response was seen | 2019–2023 earnings events | 11,313 events over 962 dates (session mapping) | all three carried: `session`, `sameday`, `nextday`; none selected | 1,000-draw block bootstrap by calendar date | h=0 β −0.21, 95% [−2.62, 10.13]; h=1 −0.37 [−3.76, 13.99]; h=2 0.06 [−3.32, 15.54]; h=5 −0.93 [−4.06, 15.46]; h=10 −3.27 [−6.80, 13.60] — all straddle zero |
| 5 | Source-stock response by surprise decile (tail-robust descriptive) — same | mean CAR(0,h) per decile, **bps** | deciles of the same scaled surprise | same | 1,131–1,132 events per decile | all three | descriptive; no interval computed | session D10−D1: **504.5 / 518.8 / 528.8 / 535.1 / 556.8** at h = 0/1/2/5/10. sameday 293.1 at h=0; nextday 216.5 |
| 6 | Source-stock drift, reported separately — same | CAR over **[+2,+20]** trading days, bps; never folded into CAR(0,h) and never used as a divisor | same | same | 11,276 events / 950 dates (session) | all three | block bootstrap by date | session β −5.50 [−27.12, −0.43]\*; sameday −5.61 [−25.40, −0.10]\*; nextday −4.88 [−17.61, −0.60]\* |
| 7 | Factor-adjusted diagnostic (accompanies, does not replace, the raw baseline) — same | market-model abnormal CAR, bps | same surprise; α,β estimated **pre-event only** on [−250, −21] | 11,277 of 11,312 (α,β) pairs estimated | 11,278 events / 960 dates | session | block bootstrap by date | h=0 β 0.04 [−2.33, 10.27]; h=10 0.10 [−1.87, 13.85] |
| 8 | ETF daily panel — `s3_etf_daily_panel.parquet`, `s3_response.parquet` | ETF daily return, bps | aggregated weighted surprise `S(f,d) = Σᵢ prior-snapshot weightᵢ × signed surpriseᵢ` summed to the ETF reaction date; sd 0.018150, p5 −0.002648, p95 0.015509 | 2019–2023 | 1,800 ETF-date cells over 928 dates | session | block bootstrap resampling whole dates jointly across the three ETFs | h=0 β 0.49 [−4.81, 6.40]; h=1 4.20 [−6.56, 10.98]; h=2 3.15 [−6.29, 9.67]; h=5 4.20 [−9.40, 11.68]; h=10 −0.64 [−10.18, 12.30]; **[+2,+20] 22.57 [12.67, 41.32]\*** |
| 9 | Daily basket tracking — `s2_tracking_daily.parquet` | ETF **minus** approximate basket, bps/day (a difference series: the common factor is already netted out) | none — an accounting comparison, weights never fitted | 2018-01-02 … 2023-12-29 | SPY 1,464 days; XLF 1,481; XLK 1,481 | n/a | n/a | SPY corr 0.9986, β 1.017, TE sd 7.3, p50 2.8, p95 12.2; XLF 0.9987 / 1.012 / 8.5 / 4.8 / 15.7; XLK 0.9993 / 1.006 / 6.3 / 2.8 / 11.2 |
| 10 | Realised accounting contribution — `s2_contributions.parquet` | `contribution_bps = 10,000 × prior-snapshot weight × source return on its reaction date`, bps | n/a — a decomposition of a realised return, not an effect | 2019–2023 | SPY 9,956 obs; XLF 1,292; XLK 1,439 | session | n/a | median \|c\| 0.24 / 1.89 / 1.61 bps; max 60.6 / 90.2 / 220.7; weight p50 0.080% / 0.740% / 0.400% |
| 11 | Macro daily rate response — `s4_rate_response.parquet` | ETF daily return, **bps per bp** of rate surprise | published FRBSF USMPD rate-futures surprise; **never** inferred from the equity return being explained; a statement and its press conference on one day are one observation | 2019–2023 FOMC days | **45** events × 3 ETFs × 5 series = 15 fitted combinations | announcement day = the trading day | 2,000-draw bootstrap | all 15 intervals straddle zero — full table in §3 below |
| 12 | Rigobon variance-regime relevance — `s4_regimes.parquet` | daily return covariance matrix over {SPY, SPY_basket, XLK, XLF}, bps² | regime indicator only | FOMC: 45 announcement vs 752 control days; earnings-dense (top quintile of summed announcing weight): 186 vs 621. Controls are 2–10 trading days either side, event days excluded; means left in, returns **not** standardised | as stated | n/a | none — a second-moment contrast, not an estimator | FOMC variance ratios SPY 0.924, SPY_basket 0.937, XLK 1.003, XLF 1.057; eigenvalue spread 1.790; condition 2,600. Micro 0.955 / 0.972 / 1.088 / 0.945; spread 2.010; condition 3,475 |
| 13 | Conditional MDE80 grid — `s5_planning_table.parquet` | minimum detectable effect, bps, at 80% power / 5% two-sided | `MDE80 = (1.96+0.84) × assumed_residual_SD / √Σ(residualised standardised surprise²)` | the 60-event registered batch | Σ of squares: event-level 58.81 (60 events), date-level 59.52 (52 reaction dates), rows-independent 74.93 | n/a | three dependence **scenarios**, not competing estimates | wholly conditional on an **assumed** 0.5–10 bps residual SD; nothing in it is estimated from the daily data |

---

## 2. Restored figures that the terminal transcript clipped

**Weekly D1 quantile ladder, source stocks** — the median was the value most
often cited in truncated form:

| quantity | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| R² contemporaneous | 0.0953 | 0.2168 | 0.3634 | 0.5180 | 0.6375 |
| R² with 4 lags | 0.1840 | 0.2934 | 0.4265 | 0.5696 | 0.6955 |
| **D1** | 0.0297 | 0.0571 | **0.1192** | 0.2518 | 0.4870 |
| β contemporaneous | 0.4140 | 0.7162 | 1.0297 | 1.3685 | 1.7647 |

By formation year (stocks): 2019 n=577 D1 0.1311 · 2020 n=578 0.1118 ·
2021 n=572 0.1767 · 2022 n=566 0.1038 · 2023 n=560 0.0924.

Lag signs, reported not selected: lag1 mean −0.0161 (49.1% positive),
lag2 −0.0148 (47.8%), lag3 +0.0137 (51.3%), lag4 −0.0325 (45.6%).

Per-instrument weekly D1 by formation year:

| | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|
| SPY | 0.0014 | 0.0032 | 0.0007 | 0.0019 | 0.0011 |
| XLF | 0.0148 | 0.0036 | 0.0182 | 0.0105 | 0.0033 |
| XLK | 0.0189 | 0.0062 | 0.0092 | 0.0058 | 0.0069 |

**Full sleeve-coverage entries.** The covered sleeve is reported as a sleeve; it
is never renormalised to 100% and called the fund, and unmapped lines are not
treated as cash or as zero-return assets.

| ETF | covered | cash | unmapped | sum | unmapped names |
|---|---|---|---|---|---|
| SPY | 98.64% | 0.08% | 0.36% | 99.09% | 24 |
| XLF | 97.26% | 0.14% | 2.24% | 99.65% | 4 |
| XLK | 99.77% | 0.15% | 0.16% | 100.08% | 16 |

Sums differ from 100% because `percent_tna` as filed does not sum to exactly
100 in every snapshot; the filed sum is shown rather than forced.

**Tracking error by holding age** (bps/day) — a rising row is the reported
snapshot going stale between filings:

| ETF | 1–5d | 6–10d | 11–20d | 21–40d | >40d |
|---|---|---|---|---|---|
| SPY | 2.6 | 2.9 | 2.9 | 2.7 | — |
| XLF | 4.7 | 4.8 | 5.0 | 4.9 | 4.3 |
| XLK | 2.3 | 2.7 | 3.0 | 3.4 | 1.6 |

Note that no row rises monotonically. This is the direct evidence for
correction C3 in §5.

**Sample funnels.**

| step | count |
|---|---|
| I/B/E/S summary rows 2019–2023 (QTR / EPS / USD, actual present) | 919,228 |
| after requiring `statpers < anndats_act` | 915,926 |
| latest pre-release consensus per (ticker, fiscal end) | 97,612 |
| consensus older than 100d moved to a ledger | 12,000 (12.3%) |
| events on securities held by SPY/XLK/XLF | 11,863 |
| outside the 2019–2023 window, removed | 550 |
| **final event registry** | **11,313** |

Consensus age at release: median 20d, p90 144d, max 628d. Link rows lacking a
`permno` 7,337; lacking an `edate` 760 (read as open-ended). Events with no
interval-valid link 2,012 (logged, never force-matched); events resolved via an
open-ended `edate` 0; events still ambiguous **0**. Pre-event price found for
100.0% of events.

Crosswalk: SPY 107 snapshots / 35,500 rows / 615 securities / median 497
holdings / top weight 4.31% / top-5 14.50%. XLF 76 / 4,705 / 84 / 66 / 12.95% /
40.77%. XLK 76 / 5,020 / 104 / 71 / 21.97% / 54.36%. Union 615 PERMNOs; held by
one ETF 435, by two 172, by all three 8.

**Report age at event, by bin** (rows):

| ETF | ≤30d | 31–60d | 61–90d | 91–120d | >120d excluded | total |
|---|---|---|---|---|---|---|
| SPY | 9,333 | 584 | 28 | 11 | 622 | 10,578 |
| XLF | 1,263 | 26 | 3 | 0 | 77 | 1,369 |
| XLK | 1,381 | 47 | 9 | 2 | 293 | 1,732 |

Excluded 992 of 13,679 rows (7.25%). `report_dt` before the event: 13,679 rows
(100%). `eff_dt` before the event: 8,509 rows (62.2%) — only the second
supports a knowable-before-the-event claim.

**Quote-field specification, as registered** (this is the pre-existing text, now
superseded in detail by `REQUEST_UNSENT.md`):

- REQUIRED — quote updates, or a clock-sampled bid/ask series, with an exchange
  or SIP timestamp and quote condition codes.
- REQUIRED — coverage of the extended session for the flagged AMC and BMO
  windows; a regular-hours-only product cannot see them.
- SUFFICIENT — a one-second bid/ask grid, for a descriptive contrast at 10
  seconds or coarser.
- NOT ENOUGH — trade-only OHLC bars: within-bar quote leadership is exactly what
  a bar aggregates away.
- NOT ENOUGH — a trade-triggered BBO sample, which observes the quote only when
  a trade happens to occur.

---

## 3. Macro coefficients in full

Daily ETF return in bps per bp of published rate surprise, 2,000-draw bootstrap,
n = 45 events for every row. All fifteen intervals contain zero.

| series | SPY | XLF | XLK |
|---|---|---|---|
| MP1 | 6.81 [−32.50, 9.89] | 9.79 [−26.10, 13.49] | 9.15 [−46.26, 13.56] |
| MP2 | −2.48 [−33.28, 9.84] | 2.57 [−28.17, 15.08] | −1.85 [−42.96, 14.32] |
| FF1 | 10.27 [−67.07, 14.68] | 13.17 [−61.77, 25.89] | 14.21 [−88.91, 16.98] |
| ED1 | −0.99 [−16.29, 9.84] | 3.45 [−13.73, 16.48] | −1.09 [−21.76, 13.35] |
| ED4 | −4.04 [−8.74, 0.72] | −1.52 [−6.32, 4.61] | −4.79 [−11.48, 1.25] |

Note the intervals are strongly asymmetric around the point estimates. That is
the bootstrap distribution of a 45-observation regression, not a sign error.

---

## 4. Reconciling the counts

### 46 FOMC census events versus 45 regression events

The 46th event is **2020-03-15**. It is an **unscheduled** emergency action
(`Unscheduled = 1`) that fell on a **Sunday**. It is therefore not a NYSE
session, has no daily equity return, and cannot enter a daily regression. It is
retained in the census — dropping it from the registry would misstate how many
policy events occurred — and is absent from the 45-observation regressions and
from the 45-day Rigobon announcement window. Nothing was filtered on outcome.

Seven of the 46 are unscheduled: 2019-10-04, 2020-03-03, 2020-03-15,
2020-03-19, 2020-03-23, 2020-03-31, 2020-08-27. Only 2020-03-15 falls off a
trading day. The six-event selection in `SELECTION_RULE.md` excludes all seven,
which is why its FOMC funnel reads 12 → 11.

### The several different date counts

These are different quantities on different bases, not inconsistencies:

| count | what it is | source |
|---|---|---|
| 978 | distinct **calendar announcement** dates in the event registry | `s1_01` census |
| 962 | distinct **reaction** dates under the `session` mapping | `s3_02` |
| 948 | distinct reaction dates under `sameday` / `nextday` | `s3_02` |
| 958 | distinct dates carrying an **ETF-event observation** | `s1_01` |
| 928 | distinct reaction dates in the **ETF daily panel** after the 120-day exclusion | `s3_02`, `s5_01` |
| 950 | dates surviving the `[+2,+20]` drift window | `s3_02` |
| 120 | dates in the acquisition manifest | `s5_01` |

978 → 962 because the session mapping routes AMC and non-trading-day releases
forward onto the next session, so several announcement dates collapse onto one
reaction date. 978 → 958 because not every announcement date has a firm held by
one of the three ETFs at the governing snapshot. 958 → 928 because the 120-day
report-age rule removes 992 ETF-event rows.

Similarly, ETF-event rows are **13,679** before the report-age exclusion and
**12,687** after; those 12,687 rows carry 9,958 distinct source events on 928
reaction dates across 583 firms. The event registry itself has 11,313 events and
597 firms. A firm can appear in the registry without ever being held by one of
the three ETFs at a governing snapshot, which is the 597 → 583 difference.

### Two inverse-HHI numbers

348 and 355 are both correct and are not the same statistic. **348** is the
inverse HHI over the 978 **announcement** dates of the event registry (`s1_01`).
**355** is the inverse HHI over the 928 **reaction** dates of the ETF panel
(`s5_01`). Both are descriptive concentration numbers. Neither is a count of
independent observations, and neither substitutes for the clustered intervals.

### Two "shared date" numbers

**98.3%** is the share of registry events sharing their **announcement** date
with another sample firm (`s1_01`). **98.6%** is the share of **ETF-event rows**
whose **reaction** date carries another sample release (`s2_01`). Different
units, different date definitions, both correct.

### Two "announcers per date" numbers — both correct

`REPORT.md` states median 33 firms share a reaction date, max 79. The stage logs
also show "announcers per cell: median 3, max 71". Both verified against
`out/`:

- **median 33, max 79, 1.5% alone** is `n_same_reaction_date` over the **11,313
  event registry** — how many sample firms share a given firm's reaction date.
  Confirmed: mean 32.23, sd 20.79, p50 33, p90 62, p99 75, max 79.
- **median 3, max 71** is `n_ann` in `s3_etf_daily_panel.parquet` — how many
  **held announcers** fall in a given **ETF-date cell**. An ETF holds only a
  subset of the registry, so this is necessarily the smaller number.

This was checked because the two looked contradictory. They are not.

---

## 5. Corrections

### Two transcription errors in `REPORT.md`

**E1 — the minimal manifest variant is 28,876, not 28,366.** `REPORT.md` reads
"minimal variant (ETFs, announcing stocks, controls only): 28,366 intervals".
The saved `s5_01` log reads 28,876, and the union role counts confirm it:
96 ETF + 60 source-stock + 28,720 matched-control = **28,876**. The full-basket
figure of 57,942 is unaffected, and so is every other number in that section.
This is a typing error in the report, not an error in the code or the output.

**E2 — nothing else.** The other flagged figure, "median 33 firms share a
reaction date, max 79", was checked against the parquet and is **correct**; see
§4. It is recorded here because it was suspected and cleared, not because it
needed changing.

No dependent module is affected by E1, so nothing was rerun. Per the standing
rule, a demonstrated source-level error would trigger a rerun of only the
affected dependent module — a report typo is not one.

### Seven interpretations narrowed, with no number changed

**C1 — twelve clock controls support bounded timing validation, not universal
second-level timestamp certification.** The clock resolution rested on three
firms over four 2023 quarters. That is sufficient to classify BMO/AMC sessions
on a bounded sample. It is **not** a certification that every `anntims` stamp in
the archive is US Eastern, and it is not evidence about second-level accuracy
for any purchased event. Each event in the six-event manifest was therefore
validated **individually** against a first-public-release source; see
`MANIFEST.md`. Read the original claim as: the session classification is
supported, the universal timestamp claim is not made.

**C2 — good daily tracking does not certify exact event-time weights.** A
0.9986 daily correlation says the reconstructed basket moves with the ETF at
daily resolution using month-old weights. It says nothing about whether the
weight vector on the afternoon of a specific announcement is the filed one.
Correlation at a coarse frequency is not accuracy at a fine one, and the
quantity of interest is a difference, where small weight errors are not diluted
the way they are in a level comparison.

**C3 — the observed daily discrepancy has not been decomposed into staleness.**
The 2.8–4.8 bps median basket error is a **total** discrepancy. It contains
weight staleness, the uncovered sleeve (0.36% / 2.24% / 0.16% of TNA),
non-synchronous closing prices, the cash line, corporate-action handling, and
ordinary approximation. No decomposition was performed and none is claimed. The
tracking-error-by-age table above is direct evidence against attributing it
mostly to staleness: XLF runs 4.7 → 4.8 → 5.0 → 4.9 → 4.3 bps across age bins,
which is flat, not rising. Saying "buying quotes will not shrink the staleness"
is correct; saying the 2.8–4.8 bps **is** staleness is not supported.

**C4 — owner approval cannot eliminate measurement error or turn an
approximation into an exact basket.** Named input 2 in `REPORT.md` asks the
owner either to supply an event-date-accurate holdings source or to accept the
approximation in writing. Written acceptance changes the **decision**, not the
**data**. If the owner accepts, the basket leg still carries error of the
measured order, that error still propagates into the ETF-minus-basket residual,
and it must still be reported alongside any estimate. Acceptance is a governance
act, not a measurement improvement.

**C5 — a large decile spread at the first close does not establish within-day
ordering.** The 504.5 bps D10−D1 spread at h=0 shows the daily response is
concentrated in the first close rather than accumulating over following days.
That is an argument for **looking** inside that day: it locates where the
variation is. It is not evidence about whether the ETF or its constituents moved
first inside that day. A daily close aggregates the entire session and cannot
order events within it, in either direction.

**C6 — the daily covariance diagnostics do not prove that any matrix inversion
is meaningless, nor that intraday identification will succeed.** `REPORT.md`
says the near-collinearity "makes any inversion meaningless". Narrow this: at
**daily** resolution, over **these** samples, with condition numbers of
2,600–3,475 and an ETF-to-own-basket correlation of 0.998, an
identification-through-heteroskedasticity estimator would be dominated by a
direction with almost no independent variation, so results from it would not be
trustworthy **here**. That is a statement about this design at this frequency.
It is not a proof about all inversions, and — importantly — it is **not**
evidence that the same contrast will be informative intraday. Whether the
variance contrast improves at higher frequency is an open empirical question,
which is precisely what the six-event pilot would begin to answer. The failure
of relevance at daily frequency is a reason to look intraday, not a prediction
that intraday will work.

**C7 — a 15-minute-endpoint MDE is not the power of the complete response curve
or of the macro-minus-micro contrast.** The planning grid is conditional on an
assumed residual SD, and it prices **one** prespecified endpoint: T to T+15
minutes. The registered estimand is a **path** across 10s / 30s / 1m / 5m / 15m
(see `ESTIMAND.md`). Nothing in the grid describes power at 10 seconds, power
for a difference **between** horizons, or power for a macro-versus-micro
contrast — that last is a difference of differences across two event families
with different variances and different session mixes, and would need its own
calculation with separate variance terms. The grid also carries no multiplicity
adjustment for evaluating five horizons. Treat it as a single-endpoint
requirement statement, which is what it was labelled, and not as the power of
the study.

---

## 6. What this addendum does not resolve

- The clock evidence is **minute-resolution**. `anntims` is a minute stamp, and
  the corroborating EDGAR times are 8-K **acceptance** times, not wire release
  instants. Horizons finer than one minute are therefore not currently
  supported. See `ESTIMAND.md`.
- The uncovered sleeve is not decomposed and not reconstructed; XLF carries the
  largest gap at roughly 3% of TNA in the snapshots governing the selected
  events.
- No claim in `REPORT.md` about the existence, price, coverage, or suitability
  of any vendor product is verified, because no vendor has been contacted.
