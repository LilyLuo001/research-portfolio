# Phase 2 analysis specification — 2023-01-24 NYSE opening-auction failure

Date frozen before opening the newly requested response files: 2026-09-23. Case selection and finite corrections are in `CASE_SELECTION.md` and `METHOD_REVIEW.md`.

## Question and interpretation

The event removed the NYSE opening-auction price-setting mechanism for 2,824 NYSE-listed securities; it did **not** close the NYSE or the cash market. The analysis asks whether valid prices and activity in continuous cash venues, SPY and the traded ESH3 contract kept the S&P 500 ecosystem mutually consistent during this disrupted opening.

This is a single-incident resilience diagnostic. SPY, ES and other cash venues are affected substitute channels, not untreated controls. The design does not identify the causal effect of ETF concentration, a DMM, or an auction in general, and does not identify the same investor moving orders.

## Frozen population, dates and clocks

- Cash basket: the 503 security issues active in CRSP S&P 500 membership series `indno=1000500` on 2023-01-23. Historical ticker mapping and prior-close capitalization are fixed by `build_sp500_roster.py`.
- Basket weights: `abs(CRSP prc) * shrout` on 2023-01-23, normalized over the 503 issues. This is a complete prior-close capitalization proxy, not the official float-adjusted S&P weight and not exact SPY NAV.
- Event: 2023-01-24. Fixed reference sessions: January 17, 18, 19, 20, 23, 25, 26, 27, 30 and 31.
- Initial collection window: 09:25:00–11:30:00 ET. It may extend for a security only to 30 minutes after a documented later operational boundary; otherwise the security is right-censored.
- Institutional markers: 09:30 failed auction/start of continuous trading; approximately 10:09 NYSE internal discovery; 10:21 member disclosure; 10:53 continued scope investigation. None is mechanically called recovery.
- One-second right-continuous grid is primary. A whole-grid +500 ms shift is the only timing sensitivity.

## Treatment/state and valid observations

Treatment is actual failure of the security's NYSE opening auction, intersected with the frozen basket. The first implementation classifies NYSE-listed basket securities from historical exchange code and validates absence/presence of the expected opening statistic/auction record in `XNYS.PILLAR`. Failed, nonfailed and unknown remain separate. The 84 LULD securities are a consequence stratum, never treatment assignment.

Each second carries venue feed availability, security status, quote validity, trade correction state and covered basket weight. Cleared quotes are not forward-filled. Valid unchanged quotes may persist; future values are never interpolated backward. As-disseminated prices and later administrative invalidation are retained as separate flags. The main price path excludes known invalid/busted executions but a companion count reports what participants saw contemporaneously.

## Market-data scope

The executable 2023 package combines `XNYS.PILLAR`, `XNAS.ITCH` and `ARCX.PILLAR` direct feeds. A cross-feed best bid and offer is labeled **three-feed composite BBO**, not NBBO, SIP or complete NMS coverage. Dataset-specific venue measures remain separate. `GLBX.MDP3` uses the actual ESH3 contract. `EQUS.MINI` starts after the event and `EQUS.SIP` is unavailable in the current account, so neither can be silently substituted.

## Constructed paths

For security `i`, form the valid named-feed midpoint each second. Let `P_i0` be its 2023-01-23 CRSP close; report

`B(t) = sum_i w_i0 * P_i(t) / P_i0`

only when covered prior-close weight is at least 95%; do not re-normalize missing constituents to one. Report covered weight and failed-auction covered weight beside every basket value. Also form SPY and ESH3 midpoint paths, normalized to the last valid observation at or before 09:29:59 ET (fallback: first valid observation in the window, explicitly flagged). ES–cash and SPY–cash measures are short-window relative-return consistency proxies, not arbitrage profits.

Primary snapshots are 1, 5, 30, 60 and 300 seconds after 09:30 and after any documented state transition with adequate support. Also report complete time paths through 11:30.

## Outcomes fixed before response inspection

1. **Cash redistribution:** per named venue, valid trade count/notional, midpoint-change seconds and MBP-1 top-of-book updates. Counts and shares are both shown; update counts are activity, not information share or capacity. Event-day tick activity is compared with the nearest pre-day (January 23); 1-second/trade outcomes use all ten references.
2. **Cross-tool paths:** fixed basket, SPY and ESH3 normalized paths; pairwise signed and absolute deviations; coverage at every endpoint.
3. **System consistency:** absolute-deviation area through 5 and 30 minutes and through the fixed collection endpoint. Normal same-clock empirical bands come from the ten sessions.
4. **Recovery:** first point after a documented disruption state at which the absolute deviation is within the predeclared normal band for 30 consecutive valid seconds. No detectable initial loss, missing support and right-censoring are distinct outcomes.
5. **Bad-data/state audit:** auction-record absence, LULD/pause/reopen messages, contemporaneously visible executions later identified as invalid, and missing correction metadata.

No VECM or Hasbrouck information share is required. It may be added once, without model shopping, only if all three stable price series have adequate common support and standard common-trend diagnostics pass outside pause/invalid states. Otherwise the paths and divergence/recovery measures are the final estimands.

### Implementation clarification after the first aggregate run

The first aggregate run exposed two implementation gaps before a substantive decision was written. They are corrected without changing the event, population, reference dates, feed set or outcome family. Activity is now reported separately for 09:25–09:29:59, the first 0–300 seconds, 301–1,800 seconds, 1,801–7,200 seconds and the full collection window; the original full-window total is retained. The recovery routine now searches for the first same-clock-band exceedance during the first 60 seconds after each documented marker and then requires 30 consecutive supported seconds back inside the band. Looking only at the marker's first second could incorrectly label a short delayed opening dislocation as “no detectable initial loss.” These finite corrections were made because the original code did not implement the stated transition-path estimand, not because a preferred sign was sought.

## Decision rule

Distinctive evidence requires more than wider spreads or volume migration already studied in exchange-outage work. Continue expanding Paper 1 only if the event shows an interpretable change in where common adjustment occurs **and** whether three-tool consistency is preserved or impaired, with valid state/coverage accounting. Mixed or null paths are reportable. A favorable ETF ranking is not a reason to switch events or add specifications.
