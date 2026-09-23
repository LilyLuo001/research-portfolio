# Phase 1 actual measurement demo

Date: 2026-09-23. Status: `COMPLETE_REAL_EXISTING_DATA_DEMO / NOT_A_CHANNEL_EVENT_TEST`.

## What actually ran

The tracked script `code/run_fomc_measurement_demo.py` ran on SCC against the existing, hash-verified FOMC equity and futures feature parquets. The sample is the first two chronological 2023 event/control pairs with complete files: 1 February/25 January and 22 March/15 March. It uses SPY XNAS venue BBO and the resolved front ES contract on GLBX, at integer-second and +500 ms shifted one-second grids.

There are eight date×grid rows and 480 derived path rows retained on SCC. All eight rows have 60/60 valid joint return bins. The primary interval is `(t0,t0+60s]`; the shifted sensitivity is `(t0+0.5s,t0+60.5s]`. No new market data were downloaded or bought.

## Main observed quantities

| Date/type | Grid/support | SPY/ES cumulative move at interval end (bp) | SPY/ES updates in 60 bins | Max early / end absolute residual divergence (bp) | Residual ratio |
|---|---:|---:|---:|---:|---:|
| 2023-02-01 FOMC | 0 ms / strict +60s | −25.36 / −25.81 | 7,963 / 8,231 | 6.72 / 4.60 | 0.69 |
| 2023-02-01 FOMC | 500 ms / +60.5s | −21.02 / −20.89 | 8,045 / 8,386 | 8.89 / 5.23 | 0.59 |
| 2023-01-25 control | 0 ms / strict +60s | +0.63 / +0.62 | 802 / 268 | 0.67 / 0.13 | 0.20 |
| 2023-01-25 control | 500 ms / +60.5s | −1.00 / −0.62 | 764 / 221 | 0.47 / 0.53 | 1.11 |
| 2023-03-22 FOMC | 0 ms / strict +60s | +45.19 / +45.45 | 4,212 / 5,122 | 3.35 / 13.88 | 4.15 |
| 2023-03-22 FOMC | 500 ms / +60.5s | +40.43 / +42.05 | 4,180 / 5,135 | 1.83 / 13.50 | 7.38 |
| 2023-03-15 control | 0 ms / strict +60s | −3.88 / −3.53 | 1,917 / 891 | 0.22 / 0.60 | 2.75 |
| 2023-03-15 control | 500 ms / +60.5s | −5.82 / −5.77 | 1,907 / 883 | 0.24 / 0.53 | 2.25 |

The FOMC rows display rapid common updating: for both events the interval-end moves have the same sign and similar raw magnitudes, while update counts are much larger than in their fixed controls. Yet the divergence proxy behaves differently across the two event pairs. On 1 February the end residual is below the early peak; on 22 March it is several times the early peak. The explicitly shifted 500 ms support preserves this qualitative contrast, but its endpoints differ by 0.5 seconds and it is not an independent experiment.

Median displayed SPY spread rose from roughly 0.50 bp in the first control to 1.98–2.35 bp on 1 February; ES median spread was about 1.23 bp versus 0.62 bp. Those are venue top-of-book states during a common-news event, not market-wide liquidity or a causal event-control estimate.

The one-second lead-balance diagnostic is positive but small in all four FOMC rows (about 0.02–0.10) and is not stable enough or structurally identified enough to rank information leadership. It is retained as a diagnostic rather than promoted to a result.

## What the demo establishes—and what it does not

It establishes that the new pipeline can separate normalized adjustment, absolute updating, top-of-book conditions and residual cross-channel consistency using real existing data, with a fixed grid sensitivity and explicit denominators.

It does not establish ETF/ES information shares, a permanent price, national NBBO behavior, complete-basket consistency, an exogenous channel restriction, or successful/failed substitution. FOMC jointly shocks both instruments and can change the ES–SPY carry relationship. The demo therefore validates measurement mechanics, not the paper's main hypothesis.

Full numerical output is `results/FOMC_DEMO_METRICS.csv`; the 480-row derived paths and their hash remain on SCC at `/project/econdept/qluo/p1_price_discovery_resilience_20260923/results/`.
