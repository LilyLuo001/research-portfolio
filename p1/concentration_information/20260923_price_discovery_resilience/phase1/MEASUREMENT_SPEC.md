# Measurement specification

Date: 2026-09-23. Version: Phase 1. Main implementation status: SPY–ES engineering demo complete; full 2015 ecology not run.

## Economic units and fixed channels

The full channel set is the same-index ETF, the active dated ES contract, and the complete contemporaneous cash basket. ETF per-share replication requires dated share quantities, cash/accruals/liabilities and corporate actions. If only index membership and pre-event weights are available, the cash object is explicitly a fixed-weight return proxy, not NAV. ES uses the actual contract and session; no event-window roll or back-adjusted continuous price is permitted. Without financing, dividend and time-to-expiry inputs, SPY–ES differences are relative-return divergence proxies rather than arbitrage spreads.

The Phase 1 demo uses SPY on XNAS and ES on GLBX. It excludes the 23-stock sample from the cash-basket label. Prices are venue BBO midpoints carried only from valid quotes observed at or before a grid point. Valid unchanged quotes remain observations. A quote cleared or invalidated is unavailable and is not filled with a future observation.

## Fixed clock, paths and denominators

The demo clock is the official 14:00 ET FOMC clock. The main grid is one second and its 60 return bins cover exactly `(t0,t0+60s]`. The sole sensitivity shifts the same one-second grid by 500 ms and is explicitly labeled `(t0+0.5s,t0+60.5s]`; it does not masquerade as the same absolute endpoints. The pre-mapping grid indices are −540 through −60. Every table reports nominal bins, actual clock offsets and valid bins.

For tool `j`, one-second midpoint return is the sum of the existing 0–100 ms and 100 ms–1 s log-return components. The displayed normalized path is the cumulative return in basis points from the event boundary. The pre-event scale coefficient is the no-intercept least-squares coefficient from SPY returns on ES returns. The divergence proxy is

`D(t) = cumulative SPY return(t) − beta_pre × cumulative ES return(t)`.

Outputs include cumulative returns at the ends of bins 1, 5 and 60, maximum absolute divergence over the first ten bins, absolute divergence at the interval end, and their ratio. For the primary grid these ends are +1, +5 and +60 seconds; for the sensitivity they are +1.5, +5.5 and +60.5 seconds. A ratio below one means the interval-end residual is smaller than the early peak; a ratio above one means divergence subsequently grew. For FOMC this is not called “resilience recovery.”

## Update, liquidity and directional diagnostics

Channel activity is the **absolute** number of native midpoint updates aggregated over the same 60 one-second bins, separately by tool. For the primary grid this is `(t0,t0+60s]`; for the sensitivity it is the explicitly shifted interval above. Relative shares may be derived only with the fixed tool set shown next to absolute counts. Median displayed spread and top-of-book depth are reported separately; they do not measure hidden or deeper liquidity.

The lead diagnostic is the difference between `corr(ES return[t−1], SPY return[t])` and `corr(SPY return[t−1], ES return[t])` over the 60 fixed bins. The complete time grid is retained before lagging; a missing bin is never replaced by the prior valid row or by a zero return. It is descriptive and low-powered. It is not an information share, causal direction or the primary result.

For the 2015 case, the same path/activity framework is applied to the complete fixed ecology. Official state intervals replace the FOMC event clock. A genuine recovery statistic will require a pre-declared consistency threshold based on pre-event dispersion, half-spreads and ticks, and 30 consecutive valid seconds after official reopening. Missing/unavailable seconds break the run; no-loss cases and right-censored non-recovery are reported separately.

## Interpretation rule

“Replacement” requires increased absolute activity in surviving channels plus limited/systematically recovering divergence. A denominator-driven activity share is insufficient. “System loss” requires degraded absolute adjustment/consistency relative to the event's own pre-state and pre-specified same-clock normal days. Common movement is not proof of correct fundamental value, and +60/+600 seconds are not treated as truth.

Short windows do not fit VECM, Hasbrouck IS, CS and state-space variants in parallel. A later common-price model is allowed only after complete economic mappings, adequate development windows, price-level/cointegration diagnostics, residual checks and correlated-innovation ordering bounds.
