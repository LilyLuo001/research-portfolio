# Refraction `L_tilt` kill test

## Status and purpose

**NOT YET TESTED; SECONDARY / MECHANISM ONLY.** The repository contains the pre-treatment exposure architecture but neither ETF Global creation/redemption data nor usable TAQ outcomes. The SCC mirror has TAQ schema/sample material only, and the owner confirmed that TAQ is unavailable. Therefore no first-stage pass or failure can honestly be reported.

The kill test asks one narrow question before any FOMC or price-discovery regression: does predetermined conversion exposure forecast a measurable increase in the ETF arbitrage/creation-redemption channel?

## Frozen construction

For successor ETF `f` and pre-event portfolio weights `w_if,pre`, define a leave-one-security-out tilt:

`L_tilt_if = w_if,pre - benchmark_weight_i,pre`, standardized within fund and frozen before the event. Aggregate only when a security appears in multiple converting portfolios, retaining fund-wave components.

The treatment clock is the first verified ETF trading/effective date. The announcement clock is separate. No post-event holdings may enter `L_tilt`.

## Ordered first-stage outcomes

1. Daily change in ETF shares outstanding and dollar fund flow.
2. Creation/redemption unit count or notional, when acquired.
3. Basket inclusion and basket weight relative to NAV holdings, when acquired.
4. Premium/discount magnitude and next-day convergence.
5. Only if TAQ is later licensed: ETF/constituent order imbalance and lead-lag response.

Outcomes 2–3 are currently blocked by the missing ETF Global/basket source; outcome 5 is blocked by TAQ. Outcome 1 can be built from CRSP/filings for covered periods and is the minimum executable first stage.

## Ex-ante pass/fail rule

The primary test is a directional event-time relation between pre-event `L_tilt` and post-event change in ETF shares outstanding/flow, estimated separately by wave. A pass requires all of:

- at least 10 independent conversion waves with a valid successor ETF series and both pre/post daily or monthly observations;
- the pooled sign matches the arbitrage-channel prediction and at least 70% of leave-one-wave-out estimates retain that sign;
- the 95% interval excludes an economically negligible effect defined before estimation as less than 0.10 pre-event flow standard deviations for a one-standard-deviation `L_tilt` change;
- placebo pre-event windows do not show the same shift; and
- no single sponsor contributes more than 50% of the signed score, or the ex-dominant-sponsor result independently passes direction and magnitude.

Failure of any item kills `L_tilt` as a claimed mechanism. It does not kill the fund-level conversion paper. No FOMC interaction is authorized until this first stage passes.

## Execution order

Acquire/construct shares-outstanding and flow first; freeze coverage and variance; run the first stage; write a one-page pass/fail decision; only then consider basket data. Do not acquire TAQ merely to rescue a failed first stage.
