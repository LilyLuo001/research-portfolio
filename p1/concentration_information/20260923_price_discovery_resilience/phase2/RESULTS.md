# Phase 2 results — activity substitution versus price-system resilience

Date: 2026-09-23. Event: 2023-01-24 NYSE opening-auction failure. Status: `REAL_DATA_RESULT_COMPLETE / INDEPENDENT_LIMITED_PASS`.

## Result in one sentence

The loss of the NYSE opening auction caused a large, visible loss of opening transaction capacity that surviving cash venues did not replace in absolute activity, yet SPY and ESH3 remained tightly aligned and the supported fixed-basket evidence does not show a broad cross-sectional price breakdown. The case is therefore best classified as **incomplete activity substitution with common-price resilience**, not “ETF volume replaced the exchange” and not “the market stopped discovering prices.”

## Population and data actually used

- Frozen CRSP S&P 500 membership on 2023-01-23: 503 security issues; 349 were historically NYSE-listed by `exchcd=1`.
- Event plus five pre- and five post-event sessions, 09:25–11:30 ET.
- Cash quotes/trades: XNYS.PILLAR, XNAS.ITCH and ARCX.PILLAR. Their cross-feed best quote is a **three-feed composite BBO, not NBBO or complete NMS coverage**.
- Index tools: SPY in the same direct feeds and the actual ESH3 contract in GLBX.MDP3.
- Weights: prior-close `abs(CRSP price) × shares outstanding`, normalized over all 503 issues. This is a transparent capitalization proxy, not official float-adjusted S&P weights or exact SPY NAV.
- Databento's event-date condition is `degraded` for XNYS.PILLAR and `available` for XNAS.ITCH, ARCX.PILLAR and GLBX.MDP3. Of 349 historical NYSE listings, 308 lack the event opening statistic with reference-day support and 41 contain an opening statistic requiring reconciliation. NYSE incident scope is therefore anchored in the SEC order; absence of one NYSE feed record is not treated as independent proof of treatment, and the final program does not export a clean failed-auction covered-weight series.

## 1. Absolute activity did not replace the missing opening mechanism

For the 349 NYSE-listed basket securities in the saved 0-through-300-second opening window, event activity divided by the ten-session same-window median was shown below. This saved definition has 301 integer-second buckets and includes the 09:35:00 bucket; it is not a strict half-open 300-bucket interval.

| Channel | Trade notional | Trade count | Midpoint-change seconds |
|---|---:|---:|---:|
| XNYS.PILLAR | 0.271 | 0.630 | 0.871 |
| XNAS.ITCH | 1.000 | 0.967 | 0.875 |
| ARCX.PILLAR | 0.886 | 0.854 | 0.826 |
| XNAS + ARCX | 0.951 | 0.931 | 0.852 |
| All three named feeds | 0.358 | 0.722 | 0.856 |

Alternative venues' share of the three-feed opening notional rose from a normal-session median of 13.3% to 35.7%. But their combined absolute notional was only 95.1% of its own normal level, not an offsetting surge. This is the paper's crucial share-versus-level distinction: market-share migration was large, while absolute alternative-venue activity did not replace the missing NYSE auction volume.

The redistribution became more visible after the first five minutes. From seconds 301–1,800, NYSE-listed notional ratios were 0.995 on XNYS, 1.170 on XNAS and 1.011 on ARCX; SPY notional on XNAS was 1.351 of its normal median. That is consistent with delayed routing and index-tool use, but it does not retroactively replace the missing opening print.

## 2. Common price discovery remained resilient

All three paths have valid pre-open anchors. At 09:30 the basket had 99.61% covered prior-close weight; from the first second onward it stayed above the predeclared 95% threshold and was typically at 100%.

- SPY–ESH3 never exceeded its same-clock 97.5th-percentile normal band during the first 60 seconds.
- Under the frozen 95%-coverage/no-renormalization estimator, basket–SPY and basket–ESH3 exceeded their bands at seconds 4, 30 and 31. Independent raw-feed decomposition shows these were not broad basket moves: MMM was the only dropped constituent at second 4 and CVS at seconds 30–31 because individually valid venue quotes produced a crossed cross-feed composite. Carrying only that name from the immediately preceding valid second puts each diagnostic gap inside the normal band.
- The stored “recovery start at second 32” is numerically correct for the frozen estimator, but it is a composite-validity/coverage diagnostic—not evidence that the economic system broadly lost and restored consistency.
- Independently recomputed opening-window deviation-area ranks were not extreme: basket–SPY ranked 4th, basket–ESH3 3rd and SPY–ESH3 4th among the event plus ten reference sessions, ranked from smallest to largest. The final program exports the event AUCs but not this cross-session rank; the review receipt preserves the recomputation.
- Through 30 minutes the ranks were 7th, 7th and 9th of 11 respectively; through the full 120-minute post-open interval they were 7th, 5th and 7th. The event was not a tail breakdown in cross-tool consistency.

The isolated cash-basket spikes later in the plot are retained rather than cosmetically smoothed. The independent opening decomposition demonstrates why a 95%-covered, non-renormalized basket can fall mechanically when one crossed-composite constituent is excluded. The main resilience conclusion therefore relies on the SPY–ES relation, contribution diagnosis, supported path, normal-day bands and area ranks—not on calling the three raw exceedances economic price discovery.

## 3. What the evidence does and does not establish

The result supports a sharper story than a generic ETF-leads-stock claim. A concentrated index complex can lose a major cash opening mechanism, fail to replace the missing transaction capacity, and nevertheless preserve a coherent common price through ETF/futures and continuous cash trading. **Execution redundancy and information resilience are different objects.**

This is a documented single-incident case study, not a universal causal estimate of ETF concentration. SPY and ESH3 are substitute outcomes, not untreated controls; the cash construct is not national NBBO; XNYS data are vendor-flagged degraded; the basket is a capitalization proxy; and no structural information-share model is estimated. Firm-specific price discovery is not identified by the common-index consistency result.

## Provisional empirical decision

`CONTINUE_PAPER / CORE_CASE_SUPPORTS_DISTINCTIVE_RESILIENCE_RESULT`.

The case passes the Phase 2 continuation criterion because it jointly measures lost activity, alternative-channel levels and common-price consistency—and yields a nontrivial separation between them. It does not support the claim that ETF/cash substitutes replaced the NYSE opening auction in activity. It does support the narrower and more interesting claim that common index price discovery was substantially more resilient than opening transaction capacity.

The bounded independent numerical review is `LIMITED_PASS`: all core arithmetic reproduces, credentials/raw rows stayed out of Git, and the decisive limitation is the one-name crossed-composite origin of all three opening basket exceedances. See `REVIEW.md` and `REVIEW_RECEIPT.json`.
