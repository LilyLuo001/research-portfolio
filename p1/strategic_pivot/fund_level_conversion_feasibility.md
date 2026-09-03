# Fund-level MF→ETF conversion feasibility

## Verdict

**HEADLINE CANDIDATE, conditional on design gates.** This is the strongest currently executable route because treatment dose is complete at the fund level: 156 completed conversions are known, 74 have verified exact dates, and 71 exact-day events across 47 waves pass the frozen N-PORT PRE/POST filing gate. That is fundamentally different from treating thousands of portfolio stocks as independent shocks with tiny ownership doses.

## Proposed question and estimand

Question: how does replacing the mutual-fund wrapper with an ETF wrapper change the fund's investor base, flows, portfolio implementation, liquidity provision demand, tax distributions, and tracking behavior?

Primary estimand: the event-time change for converted funds relative to not-yet-converted or never-converted mutual funds that were observationally comparable before the public announcement. The unit is the underlying strategy/fund, not a share class and not a held stock.

## Sample construction

1. Start from the frozen 156 completed-event register. Use the 74 verified exact dates for daily outcomes and all completed events with defensible month timing for monthly outcomes; never impute an exact day from a month.
2. Link predecessor and successor at the SEC series and CRSP portfolio levels. Aggregate share classes before matching.
3. Define risk sets by calendar month and match/coarsen on Lipper objective, active/index flag, asset class, adviser size, fund AUM, age, expense ratio, turnover, prior returns, prior flows, holdings count, concentration, and tax-distribution history.
4. Exclude target-date, money-market, fund-of-funds, non-U.S. domiciled, and noncomparable fixed-income/equity observations only through ex-ante rules. Report equity and fixed-income families separately.
5. Freeze announcement, shareholder-approval, effective, last-MF, and first-ETF dates as separate clocks; use `announcement_effective_date_architecture.md`.

## Outcomes and feasible sources

| Outcome family | Frequency | Current source | Feasibility |
|---|---|---|---|
| Net assets, returns, expense ratio, turnover, distributions | monthly/annual | CRSP Mutual Funds | Available in SCC; schema and coverage audit still required |
| Net flows | monthly | Construct from CRSP TNA and return; compare WRDS flow fields | Available; treat mergers and missing TNA explicitly |
| Portfolio composition, concentration, cash, turnover proxy | monthly/quarterly filing cadence | SEC N-PORT holdings | 71 exact events already Gate0 PASS |
| ETF shares outstanding and exchange trading | daily/monthly | CRSP stock/ETF plus SEC filings | Available through mirror coverage; 2026 extension incomplete |
| Creation/redemption and basket composition | daily | ETF Global or sponsor basket source | **Not acquired**; mechanism remains untested |
| Bid-ask and intraday efficiency | intraday | TAQ | **Unavailable in current archive** |

The primary feasible outcome should be monthly net flow and investor-demand persistence, with holdings turnover/concentration as a second family. Intraday outcomes are not a dependency for the fund-level design.

## Identification and inference

- Use stacked event-time comparisons with risk-set matched controls and calendar-time fixed effects. Avoid conventional two-way fixed-effect staggered DiD with heterogeneous treatment effects.
- Cluster at adviser and event wave where supported; report randomization inference by treated fund/wave and leave-one-sponsor-out estimates. A fund-month row is not an independent treatment.
- Estimate announcement-to-effective anticipation separately. Main post treatment begins at the realized effective/first-trade date, not at a proposal date.
- Report overlap, standardized differences, control reuse, pretrend joint tests, and effective number of treated waves before any outcome table is promoted.

## Failure and promotion gates

The design is killed as a causal headline if any of these occur: fewer than 40 exact-day treated funds retain matched overlap; fewer than 20 independent waves remain; more than 25% of treated funds lack any control inside the frozen common-support caliper; the joint pretrend rejection survives multiplicity correction in both primary control constructions; or portfolio continuity reveals strategy redefinition rather than wrapper transformation for a majority of usable events.

It is promoted if those gates pass, results survive leave-one-sponsor-out inference, and at least one pre-specified first-stage architecture outcome (ETF shares outstanding/flow channel or portfolio implementation) moves economically after the event. No downstream stock-price claim is needed for the paper to exist.
