# High-dose underlying-stock design feasibility

## Verdict

**SECONDARY / MECHANISM ONLY.** At the frozen `Exposure_pre ≥ 0.5%` threshold there are 583 stock-wave cells and 573 stocks, but only four positive-treatment waves. Dimensional supplies 562 cells across two waves; excluding Dimensional leaves 21 cells across two waves. The sample has many securities, not many shocks.

## Frozen specification

Treatment dose is predecessor-fund shares divided by CRSP shares outstanding on the last trading day strictly before the conversion wave. The threshold is inherited from the pre-outcome P1 design and was not selected using an outcome.

For earnings outcomes, the mechanism term would be `SUE × Post × Exposure_pre`. Stock and calendar-time fixed effects, wave-by-event-time controls, and industry-by-quarter controls must be declared before estimation. The estimand is local to unusually exposed stocks; it is not the average conversion effect.

## Required inference

- Treat conversion wave and sponsor as the assignment dimensions. Never cluster only by stock.
- Use wave-level sign/randomization inference, wild-cluster procedures suitable for very few clusters, and exact leave-one-wave-out displays. With four waves, asymptotic p-values cannot carry the claim.
- Show the Dimensional 2021-06-11 anchor separately, Dimensional-excluded results separately, and a pooled estimate only as descriptive.
- Freeze placebo dates and placebo portfolios before outcomes. The placebo distribution must preserve the actual number and concentration of waves.
- Use dose ranks within wave as a robustness design; do not search a new ownership cutoff.

## Interpretation limits

Even an economically large estimate would show that a handful of large portfolio positions transmit a wrapper event to underlying stocks. It would not establish a general stock-market effect. If signs change under leave-one-wave-out or the ex-Dimensional estimate is unidentified, the result remains descriptive. This design cannot rescue the original headline and should be run only after the fund-level first stage is credible.
