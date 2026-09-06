# No-purchase empirical feasibility test: ETF–stock price discovery
## Bounded execution instruction — 6 September 2026

### Objective and authority

Keep the research question fixed: do ETFs or their underlying stocks incorporate news first, and does the ordering differ between monetary announcements and firm earnings?

The owner has not authorized buying TAQ or any other dataset. Run a bounded, no-new-purchase empirical feasibility exercise using the archived WRDS data, with an optional, separately labeled public-data macro supplement. Produce actual daily/weekly results and a purchase-readiness assessment, not another novelty memo. These results cannot establish subminute leadership or guarantee publishability.

This instruction changes only the immediate measurement task in the existing price-discovery charter. It does not replace that research question or authorize reopening the conversion, fund-flow, or custom-basket projects. Preserve their execution locks and the accepted V3 checkpoint. Do not run or rewrite legacy Gate 0/1, Gate 2, or F0. Do not use invalidated outputs.

Work in `news_price_discovery/prepurchase_wrds/`. This task authorizes selective reads, preprocessing, and the explicitly described diagnostic regressions and simulations in that directory. An old restriction on inspecting treatment coefficients in a different workstream is not a ban on these diagnostics. Do not edit legacy configurations to obtain access.

### Source basis and scope

Read `P1_Refraction_WRDS_Data_Usage_Manual(2).md`. Resolve actual input paths through:

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/_migration_meta/FINAL_SCC_MANIFEST.tsv`

Canonical project root:

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/`

The manual is an inventory orientation, not a guarantee of every field or date. Inspect the actual schemas and selected records. Its P1 conversion and Refraction G7–G9 treatment restrictions still describe those older studies; do not mislabel this new auxiliary diagnostic as their primary result.

Use the already proposed instruments SPY, XLK, and XLF, after dated security/portfolio mapping. Analysis dates: 2019–2023; read necessary pre-2019 histories for lagged variables. Leave 2024–2025 unexamined for this question when genuinely uninspected; otherwise disclose prior inspection. Do not expand the research universe after seeing the diagnostic coefficients.

Cheap event censuses and daily tests should use all eligible development-period events in this bounded instrument universe, not only twelve FOMCs. The twelve-FOMC/up-to-sixty-earnings design in the existing charter concerns a prospective first intraday extraction. Keep that future selection outcome-independent.

The source-stock universe is historical reported holdings of these three portfolios, not their current constituents and not all funds in the archive. No archive-wide ETF ownership reconstruction, top-1,000-stock ranking, AUM screen, or share-class TNA reconstruction is needed.

## 1. Event and coverage census

Produce one event registry and an ETF/security crosswalk with provenance. Report unique news events, source firms, calendar dates, ETF-event observations, years, and concentration. Multiple ETFs or hundreds of constituents on a FOMC date do not create independent monetary shocks.

For earnings:

- Use actual EPS, the latest legitimate pre-release consensus, and the recovered effective-date CRSP–I/B/E/S link. Validate measure, fiscal period, currency, split basis, consensus date, and duplicate versions. Do not mix adjusted actuals with unadjusted expectations.
- Resolve the common identifier using `sdate`/`edate` and link quality, never ticker alone. Log ambiguity rather than force a match.
- The manual explicitly says `anntims` timezone semantics were not verified. Non-null time is not a verified timestamp. Seek a bounded documentation check and validate a prespecified sample against first-public-release sources. Do not turn a guessed timezone into a session classification.
- Preserve BMO, regular-hours, AMC, nontrading-day, and UNKNOWN categories only when supported. Report unresolved timing separately. If the timezone remains unknown, finish the date-level census and a clearly labeled bracketed daily event study; do not block unrelated weekly measures.
- Report competing announcements among other holdings, other identified major scheduled news, and repeated source firms. Record, rather than silently eliminate, events whose close-to-close window contains other news.
- Check same-session support for the eventual macro/micro comparison. Afternoon monetary news versus aftermarket earnings is not a clean isolated news-type contrast.

For macro:

- The manual does not establish a locally available FOMC surprise series. Use only a verified existing file or the public USMPD source described below; never infer a policy surprise from the equity return being explained.
- Retain official event dates, statement and press-conference clocks, independent rate-based surprises, units, and source version.
- Do not duplicate one daily equity return and treat statement and press conference as independent outcome observations. Whole-day diagnostic responses can use a documented whole-event surprise or jointly specified surprise components, but cannot isolate intraday chronology.

## 2. Portfolio approximation and signal size

Use selected periodic holdings only as an explicitly approximate portfolio diagnostic. Keep `portfolio_id`, ETF-security PERMNO, underlying-security PERMNO, holdings `report_dt`, availability date if verified, and analysis date distinct.

Where the field semantics and mapping are verified, portfolio weights may use `percent_tna / 100`, consistent with the accepted V3 accounting interpretation. Do not assume that V3's two positive product-date controls certify every input here. Validate selected rows and dates for the current three instruments. Do not reconstruct weights by dividing pooled holdings by ETF-class TNA. No class-dollar exposure is required.

Distinguish economic-date-prior snapshots from snapshots demonstrated available before the event. Preserve both labels; the latter alone supports a known-before-event claim. If `eff_dt` is used, apply its documented date-level interpretation, not an invented intraday timestamp. Do not use later holdings to backfill the past or interpolate between past and future snapshots.

Register a maximum report-age diagnostic rule of 120 calendar days, with fixed 30/60/90/120-day coverage bins. This is a project choice for approximate diagnostics, not proof of exact event-date weights. Observations outside the limit remain in the exclusion ledger. Do not relax it based on the response sign.

Construct a hypothetical buy-and-hold portfolio initialized at the selected snapshot and drift weights consistently with observed returns. Use a documented total-return/reinvestment convention for the daily tracking diagnostic. Retain cash separately. Missing/unmapped assets are not cash or zero-return assets. Do not renormalize a covered subset to 100% and call it the complete fund. If the complete portfolio is not computable, report the covered sleeve and its coverage, not an exact fund return or premium.

For the independently eligible diagnostic series, report daily ETF-versus-approximate-portfolio correlation, tracking-error distribution in basis points, beta, mapped asset share, report age, distribution flags, and discrepancies across successive snapshots. Do not optimize weights to maximize fit. A good fit supports construction feasibility only; a poor fit can reflect stale holdings, dividends, cash, or identifiers. Neither proves intraday leadership.

Compute the direct source-stock contribution:

`contribution_bps = 10,000 * prior_snapshot_weight * source_event_return_decimal`

Label this a realized development-sample accounting contribution, not flow, AP trade, causal news effect, price-discovery share, or a rigorous bound. EPS-related predicted responses may be estimated with a chronological training/validation split and shown separately. Use historical pre-event volatility and weights for outcome-independent sampling strata. Do not purchase only the events with the largest realized contributions.

Report contribution and source-weight distributions by ETF, source firm, year, and verified session. Construct a simultaneous-earnings ledger: a daily ETF response cannot be separately attributed to many same-day source events without acknowledging overlapping news. Prefer an ETF-reaction-date weighted-surprise aggregate for the pooled daily ETF regression.

## 3. Actual lower-frequency evidence

### 3A. Hou–Moskowitz baseline

Reproduce the basic first-stage delay construction, not the entire historical return-premium paper. For each eligible stock and annual formation date, compound daily total returns into Wednesday-to-Wednesday weekly returns. Regress approximately one year of weekly returns on contemporaneous and four weekly lags of the verified CRSP value-weighted market return:

`r_i,w = alpha + beta*r_m,w + sum(l=1..4, delta_l*r_m,w-l) + error`

Use identical rows in the restricted and unrestricted models:

`D1 = 1 - R2_contemporaneous_only / R2_with_four_lags`

Use raw R-squared for D1. Show component R-squared values, observation count, lag coefficients, and joint-lag test. Flag numerically zero/unstable denominators; do not manufacture precision with winsorization. A proposed implementation minimum is 40 complete weekly regression rows; identify it as a pilot engineering choice, not a universal theoretical threshold.

The original method uses a CRSP value-weighted market return. If that series is not verified locally, mark the original-style baseline unavailable and label any predeclared alternative benchmark explicitly as an adaptation. Do not regress SPY on itself. Do not silently replace the benchmark midway.

Apply the construction to individual stocks and, separately as an adaptation, the ETF securities. A daily four-lag version may be reported as a fixed-frequency sensitivity, not chosen in preference to weekly results based on significance. Report the sign of lag responses: the R-squared ratio itself does not establish monotonic adjustment.

These are market-response delay measures at daily/weekly resolution, not firm-news event-speed estimators, not a causal ETF-to-stock effect, and not proof of minute-level leadership.

### 3B. Earnings-response curves

Use signed earnings surprise and estimate daily cumulative response coefficients at h = 0, 1, 2, 5, 10 trading days, plus a separately reported [+2,+20] drift interval. Do not divide event returns by their realized terminal returns.

Define h=0 as the first trading day's close after the release only when timing supports the mapping. The base is the preceding trading close, so the interval includes time unrelated to the release. With unresolved clock semantics, report the fixed same-day and next-day mappings plus the bracketed multi-day window as sensitivities, without selecting the more significant mapping.

Show source-stock responses and the source-weighted contribution separately. For the ETF and portfolio daily panel, aggregate all relevant earnings surprises that map to the same reaction date:

`S_f,d = sum_i(prior_snapshot_weight_i,f,d * signed_surprise_i,d)`

Report the number and weight of simultaneous announcers and preserve source-event detail. Use a fixed, documented surprise scale, with pre-event normalization only. Raw signed responses are the baseline. A prespecified pre-event-estimated factor-adjusted diagnostic may accompany them; do not remove the exact instrument being studied by regressing SPY on itself.

Use calendar-date and repeated-source-firm dependence where relevant. Resample whole shared news dates/blocks jointly across ETFs for uncertainty. Do not treat duplicated ETF-date outcomes as independent observations. Report uncertainty and stable descriptive results even when signs are zero or opposite to the hypothesis.

A null daily lag is NOT a failed intraday project. Complete adjustment before the same daily close is compatible with ETF-first, stock-first, or simultaneous subminute adjustment.

## 4. Optional public macro supplement and variance diagnostics

Public source: Federal Reserve Bank of San Francisco, U.S. Monetary Policy Event-Study Database:

https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/

The page provides event-window changes, timestamps, and rate-based monetary-surprise construction resources. Save the actual accessed version and record coverage. This is a public external supplement, not a WRDS file. It does not provide the full ETF/constituent quote paths. Do not infer that a stock-index series is a particular ETF without checking documentation.

Use it for event counts, surprise dispersion/concentration, and coarse daily ETF/portfolio responses to rate-based news. Keep these results distinct from the existing charter's future 10-second-to-15-minute response paths. If public access fails or external supplementation is disallowed, report the macro module as specifically blocked and complete the WRDS-only modules.

Rigobon relevance diagnostic: compare daily return covariance in announcement and prespecified nearby nonannouncement windows, by news family, using consistent mean treatment and controls. Report variance ratios, covariance matrices, near-collinearity, and whether changes are approximately proportional. Do not standardize away the variance changes under study. A calendar-matched covariance contrast is not itself causal identification.

Explain that structural identification also requires stability and shock restrictions. FOMC news is not an ETF-only shock. Do not pool macro and micro regimes under a fixed transmission matrix and then claim the same exercise proves that matrix switches. A positive daily variance contrast supports exploring the method; an absent contrast does not rule out an intraday variance shift.

Report unique event/date counts and influence. Any inverse-HHI concentration measure is a descriptive effective-information statistic, not proof of independent observations or a substitute for clustered power.

## 5. Precision and acquisition decision

Estimate precision for the ACTUAL daily/weekly quantities from observed data. Do not transform daily volatility into an asserted five-minute variance by multiplying by the square root of elapsed trading time. Intraday event noise, synchronous-quote covariance, and timing accuracy are unobserved here.

Provide a clearly labeled conditional planning table for a single prespecified future horizon. Use a hypothetical ETF-minus-basket residual SD grid of 0.5, 1, 2, 5, and 10 bps per event. These values are assumptions, not measurements. For a one-standard-deviation surprise, the independent homoskedastic normal-reference approximation is:

`MDE80 = (1.96 + 0.84) * assumed_residual_SD / sqrt(sum(residualized_standardized_surprise^2))`

Do not treat replicated ETF rows as extra independent shocks. For the actual multi-ETF design report dependence-sensitive scenarios or an event-level aggregation, explicitly stating additional assumptions. The noise of interest is the ETF-minus-basket difference, including covariance, not an independent sum of the two return variances. Allow for multiple horizons when discussing eventual final inference.

Use the table to identify what intraday precision a meaningful response-gap contrast would require. It is not a final MDE estimate or a pass/fail test of the hypothesized leader.

Prepare an acquisition manifest for the existing charter's small, outcome-independently selected intraday validation batch, with exact ETF and complete constituent identifiers, dates, start/end windows, extended-session flags, and matched control windows. Count the union of security-time intervals so overlapping event windows are not purchased repeatedly. List historical-weight gaps separately: buying quotes alone cannot repair missing event-date composition.

The requested product should contain appropriate quote updates or clock-sampled bid/ask data and timestamps/conditions. Trade-only OHLC bars cannot establish within-bar quote leadership. A trade-triggered BBO sample is not the same as all quote updates. One-second quote grids may suffice for a 10-second-or-longer descriptive contrast, but cannot establish millisecond leadership; request specifications before prices. Do not require full depth or order imbalance to answer this initial quote-price question.

Do not quote stale unit prices, assume trial credits, claim a sample product covers requested historical dates, contact vendors without authority, or buy anything. A limited vendor/academic sample may be requested later; availability and access terms are not assumed.

## 6. Decision rule and finish condition

Return one of these purchase recommendations with the empirical outputs:

1. `READY_FOR_LIMITED_INTRADAY_VALIDATION`: useful event overlap, working identifiers, interpretable news-signal scale, an explicit path to event-relevant weights, and an actionable small extraction manifest. This supports seeking a no-charge sample or considering a separately approved limited purchase. It does not authorize a full data purchase or certify the hypothesis.
2. `HOLD_PURCHASE_FOR_NAMED_INPUT`: an identified non-price input such as earnings clocks or historical weights remains missing. Specify exactly what must be supplied. Do not propose a new research question or a generic further review.
3. `NO_PURCHASE_FOR_CURRENT_SAMPLE_OR_PRODUCT`: demonstrated sample/session support or product coverage cannot answer the stated contrast, or stated resource/precision constraints make the proposed acquisition unsuitable. State the scope of that conclusion; it is not proof that ETF price discovery is uninteresting.

Do not use a daily response sign, p<0.05, a daily R-squared cutoff, the old 3-bp pressure threshold, or an assumed intraday MDE as an automatic purchase gate. Do not require daily evidence of a lag when the hypothesis concerns a within-day ordering. A positive response magnitude is not proof of a delay. A statistically insignificant daily response with a wide interval is inconclusive, not proof of zero signal.

Deliver one compact package: event/coverage ledger; portfolio/signal diagnostics; delay and daily-response results with figures; optional macro results; conditional precision table and acquisition manifest; a brief purchase-readiness report; reproduction code/config/tests. No empirical result or row count may be invented from the manual.

## 7. Bounded engineering safeguards

- Inspect existing migration verification reports; do not restart a whole-archive migration/checksum exercise merely for this task.
- Search the manifest once, distinguish overlapping legacy/CIZ/rescue sources, and read only needed columns, selected ETF portfolios, securities, dates, and warm-up histories.
- Select a primary daily source and compare overlap on a small sample. Do not stack legacy and CIZ duplicates or mix price returns and total returns silently. Extract ETF securities separately from common-stock filters.
- Complete a few raw-record round trips and one selected event before processing the bounded sample. Test return units, mapping intervals, consensus precedence, weights, split/distribution handling, session mapping, duplicate events, and nested regression rows.
- Test a write on the selected output filesystem before computation. Retain licensed data privately. Record code/config/source hashes, write stage/event checkpoints atomically, and show measured progress.
- One concurrent research job maximum. No automatic whole-pipeline restart. On failure, preserve outputs, diagnose the failed stage, make at most one targeted correction/retry under this assignment, then return the remaining concrete blocker if still unresolved.
- A failed optional module does not prevent reporting independently valid results from other modules. Do not modify unrelated jobs or upload credentials.
- Finish after this one bounded empirical package. Do not append a new literature/positioning assignment or expand the pipeline after seeing the first results.

### Method references, separate from archive facts

Hou and Moskowitz (2005), *Review of Financial Studies*, "Market Frictions, Price Delay, and the Cross-Section of Expected Returns," pp. 985–986, defines the basic weekly/four-lag D1 construction. The current selected-ETF application is not a replication of their entire sample or second-stage portfolio procedure.

Rigobon (2003), *Review of Economics and Statistics*, "Identification Through Heteroskedasticity," motivates the variance-regime diagnostic, but does not justify recovering unobserved intraday timing from daily prices.

FRBSF USMPD supplies a free external macro-news supplement. It is not part of the attached WRDS archive and not a substitute for constituent quote histories.
