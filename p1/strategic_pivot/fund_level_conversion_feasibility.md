# Fund-level MF→ETF conversion feasibility

## Verdict

**SUPERSEDED AS AN EXECUTION AUTHORITY by the 2026-09-06 post-V3 decision.** The
fund-level route remains a research candidate, not a currently executable
headline. There are 156 known completed conversions and 74 verified exact dates.
A legacy artifact records 71 events/47 waves with PRE/POST N-PORT filing
coverage. That descriptive count is unaudited under V3; its old Gate0/PASS
label is invalid and does not establish eligibility or continuity. See
`POST_V3_RESEARCH_DECISION-2026-09-06.md`.

## Proposed question and estimand

Question: how does replacing the mutual-fund wrapper with an ETF wrapper change
observable strategy-boundary demand, portfolio implementation, tax
distributions, and tracking behavior? Public fund data alone do not identify
investor origin or the full investor base.

Candidate primary estimand: the event-time change in strategy-boundary net
capital, after separately labelling documented inherited/transferred assets and
documented class transfers, relative to not-yet-announced or never-converting funds
that were comparable before the public announcement. Unresolved sources remain
an unidentified residual. The unit is the underlying strategy/fund, not a share
class or held stock.

## Sample construction

1. Start from the frozen 156 completed-event register. Monthly eligibility requires a verified announcement/assignment month and a first complete post-ETF month; exact-day verification gates only daily outcomes. Never impute an exact day from a month.
2. Link predecessor and successor at the SEC series and CRSP portfolio levels. Aggregate share classes before matching.
3. Define risk sets by calendar month and match/coarsen on Lipper objective, active/index flag, asset class, adviser size, fund AUM, age, expense ratio, turnover, prior returns, prior flows, holdings count, concentration, and tax-distribution history.
4. Exclude target-date, money-market, fund-of-funds, non-U.S. domiciled, and noncomparable fixed-income/equity observations only through ex-ante rules. Report equity and fixed-income families separately.
5. Freeze announcement, shareholder-approval, effective, last-MF, and first-ETF dates as separate clocks; use `announcement_effective_date_architecture.md`.

## Outcomes and feasible sources

| Outcome family | Frequency | Current source | Feasibility |
|---|---|---|---|
| Net assets, returns, expense ratio, turnover, distributions | monthly/annual | CRSP Mutual Funds | Available in SCC; schema and coverage audit still required |
| Net flows | monthly | Construct from CRSP TNA and return; compare WRDS flow fields | Available; treat mergers and missing TNA explicitly |
| Portfolio composition, concentration, cash, turnover proxy | monthly/quarterly filing cadence | SEC N-PORT holdings | Legacy 71-event coverage count is unaudited under V3 and does not establish eligibility/continuity |
| ETF shares outstanding and exchange trading | daily/monthly | Candidate CRSP stock/ETF plus SEC sources | Not validated for the full sample; source, schema, split/NAV reconciliation, and coverage audits required |
| Creation/redemption and basket composition | daily | ETF Global or sponsor basket source | **Not acquired**; mechanism remains untested |
| Bid-ask and intraday efficiency | intraday | TAQ | **Unavailable in current archive** |

The primary feasible outcome should be monthly net flow and investor-demand persistence, with holdings turnover/concentration as a second family. Intraday outcomes are not a dependency for the fund-level design.

## Identification and inference

- Use stacked event-time comparisons with risk-set matched controls and calendar-time fixed effects. Avoid conventional two-way fixed-effect staggered DiD with heterogeneous treatment effects.
- Cluster at adviser and event wave where supported; report randomization inference by treated fund/wave and leave-one-sponsor-out estimates. A fund-month row is not an independent treatment.
- Estimate announcement-to-effective anticipation separately. Assignment begins at the first public filing/announcement; monthly post outcomes begin in the first complete post-ETF month, while daily market outcomes use the verified first-trade date.
- Report overlap, standardized differences, control reuse, pretrend joint tests, and effective number of treated waves before any outcome table is promoted.

## Historical proposed gates — not operative

Any future causal design must define eligibility only from information available
by assignment: legal identity, mandate, benchmark, manager, asset class, and
announced concurrent changes. Realized post-event holdings continuity is a
reported diagnostic, not a retrospective sample filter. Historical proposals
for minimum treated events, waves, overlap, and pretrend performance are not
current machine gates and may not authorize construction. Any future thresholds
or daily extension require a separately frozen specification and pilot.

Promotion is `NOT YET`: the bounded current-literature comparison must first
confirm that the audited capital-flow bridge remains distinct, then the separate
`F0_FUND_FLOW_BRIDGE` pilot in the post-V3 memo must establish outcome and donor
support without estimating a post-treatment coefficient.
