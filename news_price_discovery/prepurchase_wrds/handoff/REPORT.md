# Purchase-readiness report

No-purchase empirical feasibility test for the ETF–stock price-discovery
question. Instruments SPY, XLK, XLF; analysis window 2019–2023; archived WRDS
mirror on SCC plus one public macro supplement. Every number below comes from
code in `src/` executed on the real archive; logs are in `$PPW_WORK/logs`.

Nothing here establishes subminute leadership, and nothing here was intended to.

## Decision

**`HOLD_PURCHASE_FOR_NAMED_INPUT`**

The empirical feasibility work is complete and it came out favourably: the
sample is large enough, the basket is reconstructable, the clock is resolved,
and the signal is concentrated exactly where intraday data would look. The hold
is not caused by a weak result. It is caused by two inputs that cannot be
obtained from inside this exercise.

### Named input 1 — a written product specification confirmation

Confirmation, obtained by the owner, that a specific product delivers **all
four** of the following for the 587 securities and 120 dates in
`out/s5_acquisition_manifest.parquet`:

1. quote updates, or a clock-sampled bid/ask series at 1 second or finer, with
   an exchange or SIP timestamp and quote condition codes;
2. **extended-session coverage**, because 79.1% of the requested intervals fall
   outside 09:30–16:00 ET. This is the binding requirement and it follows
   directly from the measured session mix: 56.5% of releases are BMO and 42.8%
   are AMC, so only 0.3% arrive during regular hours;
3. coverage of the **historical** dates 2019–2023, not a recent sample window;
4. delivery as a quote stream, not trade-only OHLC bars and not a
   trade-triggered BBO sample.

I have not contacted any vendor, quoted any price, assumed any trial credit, or
verified that such a product exists. Specifications must be requested before
prices, and that request requires the owner's authority.

### Named input 2 — a decision on basket-weight staleness

The ETF-minus-basket residual is the outcome of interest, and the basket can
only be built from monthly reported holdings. Measured consequences:

- median snapshot age at an event is 22 days; 37.8% of ETF-event rows have no
  `eff_dt` before the event, so their weights are not demonstrably knowable in
  advance;
- the resulting **daily** basket error is 2.8–4.8 bps median, sd 6.3–8.5 bps.

That error sits inside the same 0.5–10 bps range as the entire assumed residual
grid in the planning table. Buying quotes does not shrink it. The owner must
either supply an event-date-accurate holdings source, or accept in writing that
the basket leg carries approximation error of this order — which may exceed the
effect being measured. This is a gap in the weight record, not in the quote
data, and the two should not be conflated in a purchase decision.

Neither input is a request for generic further review, and neither proposes a
new research question.

## What was established

**Sample.** 11,313 earnings events, 597 firms, 978 calendar dates, ~2,250/year
evenly spread; 13,679 ETF-event observations over 958 dates. 46 FOMC events on
46 distinct dates from the FRBSF USMPD (sha256 recorded in
`logs/s1_02_clock_and_macro.lineage.json`).

**The clock, previously unresolved, is resolved on a bounded sample.** The
archive manual records that the `anntims` timezone was never verified. A rule
fixed before any stamp was read — the largest position in each ETF at the final
2023 snapshot — selected AAPL, MSFT and BRK.B. Apple's stamps read 16:30:00 on
all four 2023 quarters against a publicly reported ~4:30 p.m. ET release;
Microsoft's read 16:01–16:05; Berkshire's four dates are all Saturdays. No
timezone offset reproduces all three patterns at once unless the field is US
Eastern. Scope: 12 events, three firms. Sufficient to classify sessions, not a
universal certification.

The classification pays for itself. Under the session mapping the top-minus-
bottom surprise decile spread is **504 bps at h = 0**; under a naive same-day
mapping it is 293 bps and only reaches 508 bps a day later (`fig3_spread.png`).
That gap is the AMC releases being routed correctly. All three mappings are
carried through every result regardless, and the more significant one is never
selected.

**Basket reconstruction works.** Daily correlation between each ETF and its
approximate portfolio is 0.9986 / 0.9987 / 0.9993 (SPY / XLF / XLK), beta 1.02 /
1.01 / 1.01, median tracking error 2.8 / 4.8 / 2.8 bps. Weights are never fitted
to improve this. The covered sleeve is 98.6% / 97.3% / 99.8% of reported TNA and
is reported as a sleeve, never renormalised to 100% and called the fund.

**The response is concentrated at the first close.** The raw OLS slope on the
price-scaled surprise is uninformative and is reported as such: two Chesapeake
Energy events at a sub-dollar price carry 79.7% of the regressor variance.
Nothing was winsorised. The tail-robust decile summary is monotone across all
ten deciles and the D10−D1 spread runs 504 → 519 → 529 → 535 → 557 bps at
h = 0, 1, 2, 5, 10. Essentially the whole daily response is already in the first
close, which is the case for looking inside that day rather than against it.

**Delay measures.** Hou–Moskowitz first-stage D1 on 2,853 stock-formations has
median 0.119, mean 0.200. The same construction applied to the three ETFs as a
declared adaptation gives median 0.006 (SPY 0.0007–0.0032 across formation
years). The CRSP value-weighted return was verified locally in stage 7, so this
is the original-style baseline with no benchmark adaptation, and SPY is never
regressed on itself. These are market-response delay measures at weekly
resolution. They are not firm-news event-speed estimators and not evidence of
minute-level leadership.

**Macro module completed, and it is the clearest negative.** Daily ETF responses
to the published rate surprises are zero-centred across all five series and all
three ETFs over 45 events. The Rigobon relevance diagnostic explains why the
daily frequency cannot carry this design: announcement-day variance ratios
against calendar-matched control windows are 0.92–1.09, i.e. FOMC days are not
detectably more volatile than nearby non-FOMC days at daily resolution; and the
ETF is 0.998 correlated with its own basket in every regime, leaving the
covariance matrix near-singular (condition number 2,600–3,475). The generalised
eigenvalue spread is 1.79, so the change is not purely proportional, but the
near-collinearity makes any inversion meaningless. Relevance fails on the data,
not on the code. This is a direct argument that the intraday window is where the
variance contrast would have to come from — it is not causal identification, and
an FOMC decision is a shock to the ETF and its constituents alike.

## Precision

Measured, from observed data with the dependence the sample actually has: the
achieved 95% half-width on the ETF daily response is 5.6 bps per unit surprise
at h = 0, block-resampled by whole calendar date across the three ETFs. 98.6% of
ETF-event rows share a reaction date with another sample release; median 33
firms share a reaction date, max 79; only 1.5% of events are alone. The
inverse-HHI effective number of dates is 355 against 928 nominal — descriptive
only, not a proof of independence and not a substitute for the clustered
intervals.

Assumed, for a single prespecified future horizon (release time T to T+15
minutes, quote-clock sampled at 1 second):

| assumed residual SD (bps/event) | MDE80 event-level | MDE80 date-level | rows-independent |
|---|---|---|---|
| 0.5 | 0.183 | 0.181 | 0.162 |
| 1.0 | 0.365 | 0.363 | 0.323 |
| 2.0 | 0.730 | 0.726 | 0.647 |
| 5.0 | 1.826 | 1.815 | 1.617 |
| 10.0 | 3.651 | 3.629 | 3.235 |

The grid is an assumption grid. The daily ETF-minus-basket dispersion was **not**
multiplied by the square root of elapsed trading time to produce it; doing so
would assert the intraday variance structure the project exists to measure. The
three columns are dependence scenarios, not competing estimates; the
rows-independent column is shown only to size the overstatement that treating
replicated ETF rows as separate shocks would produce. The noise is the
difference series, which nets out the common factor, not the sum of two return
variances.

## Acquisition manifest

`out/s5_acquisition_manifest.parquet`. 60 earnings events drawn stratified on
pre-event volatility, prior-snapshot weight and verified session across 31
strata, 53 firms and 5 years, plus 12 FOMC events stratified by year. The draw
is seeded and uses only pre-event information, so it is not the set of events
with the largest realised contributions.

- union of distinct security-time intervals: **57,942** (overlaps counted once)
- 587 securities, 120 dates, 49,863 security-days
- 79.1% of intervals need extended-hours coverage
- minimal variant (ETFs, announcing stocks, controls only): 28,366 intervals

The minimal variant is roughly half the size but cannot answer the stated
question, because ETF-minus-basket requires the basket. Both are listed so the
cost of the basket leg is visible before anything is priced.

## Scope and limits

A daily response coefficient measures how much of a surprise is in a day's
close. It does not order the ETF against its constituents inside the day. The
zero-centred macro coefficients and the flat post-h=0 decile spread are
inconclusive about intraday leadership, not evidence against it; a null daily
lag is not a failed intraday project. The realised
`contribution_bps = 10,000 × prior-snapshot weight × source return` is an
accounting decomposition of a realised return — not a flow, an AP trade, a
causal news effect, a price-discovery share, or a bound. The 120-day report-age
rule is a registered project choice, not proof of exact event-date weights;
the 992 excluded rows stay in `out/s2_exclusion_ledger.parquet` and the rule was
never moved after seeing a response sign.

## Disclosure

The 2023 I/B/E/S summary file carries fiscal periods announced in early 2024. A
count-level view of them (550 events, 49 dates, no returns read) was produced
incidentally on the first census run before the window filter was applied. Early
2024 is therefore not claimed to be uninspected. 2024–2025 is otherwise
uninspected.

## Figures

| file | content |
|---|---|
| `figures/fig1_delay.png` | D1 distribution, stocks vs ETFs, and by formation year |
| `figures/fig2_response.png` | decile response curves under all three mappings |
| `figures/fig3_spread.png` | D10−D1 spread by horizon; the session-mapping gap |
| `figures/fig4_precision.png` | conditional MDE80 grid and measured daily basket error |
