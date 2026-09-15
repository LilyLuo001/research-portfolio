# Outcomes-blind supplemental pull plan

## Decision

Do not spend the remaining credits on more dates for the current eight names yet. First use the already cached N-PORT history and existing SCC sources to construct the design variables that determine whether a quotation request belongs in the P1 estimand. The current bottleneck is not raw holdings availability: cached filing metadata shows historical reports back to 2019 for all five planned old waves, and W016 alone has 12 cached reports before the verified 26 August 2022 announcement. The bottleneck is an auditable pre-announcement reconstruction, event/session eligibility, and rank-aware selection.

The supplemental sample should follow the original decision-pilot hierarchy, not create a new stock-ETF fallback:

1. **Stage A — 24 stock-wave units:** W002, W013, W021/JPEF and W025; exactly three high and three low names per package after the full eligible universe is tiered. Require eight PRE-announcement and four POST-implementation quarterly releases per selected stock when available. This is the minimum balanced design-development gate.
2. **Stage B — 32 stock-wave units:** expand each main package to four high and four low names, stratifying within each tier into two lower-liquidity and two upper-liquidity names as in the original plan. Do this only after Stage A passes event/session and rank gates.
3. **Stage C — up to 40 stock-wave units:** add W016 as eight-stock Bridgeway stress evidence, four high/four low. Keep it outside the main four-package pooled precision result because the original plan identifies it as a stress package and its conversion date coincides with the March 2023 banking shock.

Twenty stocks is an inferior stopping point because four waves cannot be evenly split into equal high/low counts. If the user imposes 20, alternate 2H/3L and 3H/2L by wave and report unequal weights. Prefer 24.

## Stage 0 fields to build before selecting any name

For each constituent fund in each candidate package, produce one signed, versioned row with:

- fund series ID, CIK, legal trust, adviser and ultimate economic sponsor; predecessor-to-ETF mapping; package membership and whether synchronized constituents are one package;
- earliest independently verified public announcement date/time, source accession/URL, time precision and earliest plausible instant; implementation/legal-effective and first-trading instants;
- latest holdings report strictly before the earliest plausible announcement, filing/publication date, all position identifiers, unadjusted shares and split factor;
- contemporaneous CRSP shares outstanding and validity interval, corporate actions, historical PERMNO/CUSIP link, and the resulting `D_iw` numerator and denominator;
- complete other-conversion membership over `[A_w-24 months,A_w+24 months)` and exclusion reason;
- signed sponsor-component ID. Raw adviser text remains a proxy, not a final inference cluster.

W021 must be rebuilt at the fund/package level: the old W021 effective-date bucket contains both JPMorgan Equity Focus Fund and JPMorgan Limited Duration Bond Fund. The equity JPEF sample must not inherit bond-fund constituents or an announcement clock by date-only pooling.

Tier all eligible positive exposures before looking at earnings coverage. Use the contract's proposed empirical inverse-CDF rule only if the PI signs it; do not split ties. Record `q1`, `q2`, low/middle/high counts and the absolute high-low dose gap. If the rule is not signed, stop at a ranked exposure roster rather than inventing final tiers.

## Outcomes-blind stock selection

Within each signed package, apply these gates in order:

1. Strict pre-announcement positive exposure and valid denominator/corporate-action history.
2. No competing conversion in the specified window; no reused security that links otherwise separate sponsor components.
3. At least eight usable PRE announcements and four usable POST announcements, with event identity, timestamp/timezone/precision and accounting-period identity verified before any response is read.
4. For the RTH candidate estimand, at least 60 trading minutes between release and actual close, open inclusive and close exclusive. Non-RTH events are retained as a separately labelled diagnostic population, not substituted into the primary rule.
5. Candidate stock and SPY have requestable same-source windows covering the common six horizons; actual live-state coverage remains a post-download eligibility check.
6. Within high and low tiers, split the PRE-announcement liquidity distribution in half using a frozen CRSP metric (for example median daily dollar volume over trading days `[-250,-21]` before `A_w`) and select equal counts from each half. Break ties by PERMNO, never by surprise or return.
7. Prefer names that create common PRE and POST calendar-quarter support across both tiers and preserve more than one stock per tier after all gates. Before purchase, construct the symbolic design matrix using event IDs, stock, industry, quarter, group and period. Reject a wave if load-bearing columns are deterministically aliased even before SUE values are inserted.

## Earnings/SUE and quote pull after the roster freezes

The SCC schema receipt confirms local availability for 2019–2024 of IBES actuals, IBES detail forecasts, CRSP daily stock and shares history. Pull only the frozen roster/event rows and retain:

- unique economic event ID, announcement and activation clocks, fiscal-period key and quarterly/annual duplicate-resolution flag;
- actual EPS, each analyst's latest forecast strictly within 90 calendar days before release, analyst count, currency, primary/diluted and accounting-basis compatibility;
- prior-price scaling date/value, split consistency and the unique-event PRE-first-announcement SUE calibration SD;
- CRSP `RETX`, SPY return and at least 120 usable days in `[-250,-21]` for the beta regression;
- historical exchange open/close/half-day instants, industry code and response-leg trading dates.

Then compile Databento requests only for eligible event windows. Preserve stock and SPY on the same source. The current XNAS one-second data are a venue-specific development source, not SIP NBBO. Include a fixed update-level validation subset and do not treat one-second records as independent events. Use the remaining credit only after an exact deduplicated cost quote; no purchase is authorized by this memo.

## Decision gates after each stage

- **Measurement gate:** direct BBO fields parse; two-sided live state exists at all six horizons for both stock and SPY; missing/withdrawn states are distinguished; source sensitivity is reported.
- **Design gate:** every main wave has nonempty high and low groups, at least two stocks per tier, observed support for every positively weighted stock/calendar cell, and full column rank for the frozen estimator.
- **Inference gate:** build the dependency graph over unique economic events, shared stocks, signed sponsor/package membership and every response-leg date. Report component count, maximum component score share and leave-one-component sensitivity. Four main packages remain a few-component design even if there are hundreds of one-second rows.
- **Power gate:** only after the PRE design passes rank, estimate covariance from genuinely eligible PRE events through the exact frozen estimator. Report conditional projected precision for Stage B and a larger confirmatory design. Do not compute retrospective power from a treatment estimate or call duplicated stack rows effective sample size.

If Stage A cannot produce four estimable main waves, stop procurement and report which field/gate failed. Adding more intraday rows or POST dates cannot repair invalid treatment timing, a missing tier, or a collapsed dependency graph.
