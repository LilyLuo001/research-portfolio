# P1 native-tick mechanism pilot: coactivity is real, event-specific price discovery is not established

Date: 2026-09-22. Decision: **`COACTIVITY_ONLY`**.

## Result at a glance

- **Data:** 18/18 requested venue-window files, 12,298,752 native `mbp-1` records (280,208,005 compressed bytes). Purchased files contain 513,606 trades; after excluding the state lead/tail, the fixed analysis windows contain 264,831 stock trades and 217,189 SPY trades. Sources are XNAS.ITCH and ARCX.PILLAR, analyzed separately; they are not SIP/NBBO.
- **Direction:** in the fixed analysis windows, 85.44% of trades have native aggressor side; midpoint fallback classifies 10.47%; 4.09% remain unknown. The quote-response identity holds to a maximum absolute error of `2.28e-13` bp.
- **Main coactivity:** AAPL has positive excess stock–SPY pairs within ±20 µs in every RTH and ordinary control window, across both venues and both event/receive axes. XOM is approximately zero. The AAPL signal survives excluding the first 200 ms of each second.
- **Critical comparison:** every matched AAPL ordinary control window has *more* excess coactivity per 1,000 stock trades than its post-earnings RTH window. February: RTH `16.76/9.28` versus control `37.73/21.00` on ARCX/XNAS. August: RTH `22.15/16.33` versus control `64.08/54.65`.
- **Quote response:** paired AAPL/SPY trades often have larger five-second signed midquote changes than unpaired trades, but the same pattern is present on control days. XOM paired counts are only 0–7 usable trades per instrument/venue cell. This is evidence of high-speed coactivity, not evidence that earnings information or ETF arbitrage caused it.
- **Announcement windows:** AAPL has large stock-specific quote paths, but exact ±20 µs counts are sparse or background-sensitive; XOM has no near pairs. The candidate timestamps are minute-level anchors and cannot identify subsecond leadership.
- **Cost:** API quote was `$1.365348368882`, below the `$10` self-cap, and all files downloaded. A posted account debit was not independently observable, so quote is not relabeled as an invoice.

The pilot therefore validates the engineering claim that Databento direct-feed ticks can measure an Ernst-style near-synchronous pattern. It does **not** show an earnings-specific increase, stock-to-ETF or ETF-to-stock leadership, an entire-basket mechanism, concentration causality, or a new paper contribution.

## 1. Fixed sample and implementation

The sample contains AAPL–SPY and XOM–SPY on two direct venues. Module A retains three candidate announcement minutes; module B uses 10:00–11:00 ET on the first RTH session following the announcement; module C uses the same hour on the fifth prior trading day. Each query includes a two-minute state lead and 65-second tail, which are not counted as main matching time.

The primary distance is `d = t_SPY - t_stock`. Near pairs use `[-20,+20)` µs. Local background uses `[-1200,-1000)` and `[1000,1200)` µs, so:

`excess = near - 0.1 × background`.

The ±100 µs and ±1 ms results remain in `PAIR_COUNTS.csv`; no threshold replaced the fixed ±20 µs result. Counts use sorted range searches, not a stock-by-SPY Cartesian product. The main clock is `ts_event`; `ts_recv` is a receive-axis sensitivity and is never called SIP time.

Trade direction uses the documented native aggressor side first. Only records with source side `N` use a strict prior-message midpoint fallback; an at-mid or otherwise unresolved trade stays unknown. Across the purchased files, 438,478 of 513,606 `T` records use native side, 54,347 use midpoint fallback and 20,781 remain unknown. Inside the fixed analysis windows, the corresponding counts are 411,837, 50,457 and 19,726 out of 482,020. Seventy `F` records are excluded as separate economic trades to avoid trade/fill double counting. There are zero bad-receive-timestamp or maybe-bad-book flags.

The two-minute request lead and 65-second request tail are used only to initialize or complete quote endpoints. They are excluded from pair counts, histograms, paired-group assignment, response-trade centers and main trade denominators: 31,586 trades are support-only. Independent review identified an initially overinclusive implementation; all displayed results are from the corrected rerun.

## 2. Main ±20 µs results

All entries below are excess pairs per 1,000 stock trades on the event-time axis. “Periodic” removes records in the first 200 ms of every second.

| Window | ARCX main | XNAS main | ARCX periodic | XNAS periodic |
| --- | ---: | ---: | ---: | ---: |
| AAPL Feb announcement | -49.94 | -6.84 | 0.84 | 0.15 |
| AAPL Feb post-announcement RTH | 16.76 | 9.28 | 17.67 | 8.72 |
| AAPL Feb ordinary control | 37.73 | 21.00 | 36.29 | 17.04 |
| AAPL Aug announcement | 1.80 | 1.20 | 1.37 | 0.13 |
| AAPL Aug post-announcement RTH | 22.15 | 16.33 | 18.33 | 14.72 |
| AAPL Aug ordinary control | 64.08 | 54.65 | 55.96 | 50.17 |
| XOM Jan announcement | 0.00 | 0.00 | 0.00 | 0.00 |
| XOM Jan post-announcement RTH | -1.13 | 0.30 | 0.24 | -0.11 |
| XOM Jan ordinary control | 0.91 | -0.24 | 0.36 | -0.14 |

For AAPL RTH and control windows, nearly all positive excess is in same-direction `B_B` and `S_S` pairs. The pattern remains positive on `ts_recv`, although its magnitude generally falls. The February after-hours window is not robust: it changes from strongly negative on the event axis to near zero or positive on the receive axis and after the periodic exclusion. It cannot anchor a mechanism claim.

Increasing the symmetric matching band to 100 µs or 1 ms mechanically increases pair counts and does not reverse the central ranking: AAPL controls remain at least as coactive as the post-announcement RTH windows. Threshold results and the ±5 ms histograms are preserved, not selected after seeing outcomes.

## 3. Five-second quote response

The most informative cells are AAPL RTH and matched controls. Values are mean signed midquote changes in basis points after a signed trade; they are descriptive within venue/window, not causal estimates.

| Window/venue | Stock paired (n, bp) | Stock unpaired bp | SPY paired (n, bp) | SPY unpaired bp |
| --- | ---: | ---: | ---: | ---: |
| Feb RTH ARCX | 247, 1.75 | 1.75 | 310, 1.13 | 0.20 |
| Feb RTH XNAS | 416, 2.63 | 1.77 | 373, 0.78 | 0.20 |
| Feb control ARCX | 122, 1.33 | 0.68 | 156, 0.65 | 0.20 |
| Feb control XNAS | 230, 0.91 | 0.52 | 145, 0.43 | 0.17 |
| Aug RTH ARCX | 133, 0.78 | 0.36 | 181, 0.52 | 0.16 |
| Aug RTH XNAS | 160, 0.42 | 0.46 | 248, 0.56 | 0.15 |
| Aug control ARCX | 134, 0.71 | 0.39 | 241, 0.39 | 0.17 |
| Aug control XNAS | 187, 0.46 | 0.39 | 220, 1.03 | 0.17 |

Paired SPY trades have larger average five-second signed changes in all eight AAPL RTH/control venue cells. Paired stock trades are larger in seven of eight cells. But ordinary controls display the same association, often with higher coactivity rates; pair membership also selects unusual trading intensity and is not randomized. The response is therefore compatible with common fast trading or shared information, not uniquely with ETF transmission. XOM has too few same-direction paired observations for a stable response comparison.

One-, five- and sixty-second means, medians and interquartile ranges; pre-trade quoted spreads; sizes; and exact identity checks are in `TRADE_RESPONSE.csv`. Missing endpoints are excluded, never filled with zero.

## 4. What the announcement paths add

The tick paths confirm that AAPL moved sharply relative to SPY after both candidate minutes on both venues. XOM also moved sharply while SPY moved little. These paths are useful descriptive checks, but they do not locate the exact public-release instant within the candidate minute. The sparse/unstable microsecond pair counts show why minute-level news clocks cannot be reverse-engineered from the price path.

The two-security path is not a full SPY basket and cannot support Hasbrouck/Gonzalo–Granger claims about a common efficient price. It also cannot tell whether the ETF caused the stock move, the stock caused the ETF move, or both responded to a third message.

## 5. Decision and one next action

**Decision: `COACTIVITY_ONLY`.** The native data, timestamp handling, direction recovery and quote-response machinery are usable. The specified three-event sample does not produce an earnings-specific mechanism pattern: normal AAPL control hours have stronger near-synchronous coactivity, XOM is essentially absent, and the after-hours result is sparse or clock-sensitive. This is not a zero-effect result for the broader market; it is a stop on interpreting these three events as evidence that ETF trading took over price discovery.

**Only next action:** use this now-validated code in one predeclared, larger RTH panel that crosses constituent ETF weight/concentration with earnings versus matched ordinary days. The design must estimate an interaction or difference-in-differences in coactivity/response, not merely count more positive pairs. Do not buy more windows for these same three cases or claim novelty from reproducing the unconditional synchronization fact; the new panel is justified only if its contribution is explicitly the concentration-dependent allocation of macro/common versus stock-specific price discovery.

Independent recomputation is reported in `INDEPENDENT_REVIEW.md`. Machine-readable inputs and full results are in `EVENT_SUMMARY.csv`, `PAIR_COUNTS.csv`, `TRADE_RESPONSE.csv`, `FILTER_COUNTS.csv`, `QUOTE_DIAGNOSTICS.csv` and `SOURCE_SEMANTICS_COUNTS.csv`. Raw DBN remains on SCC.
