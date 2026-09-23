# Phase 2 — bounded independent method review

Date: 2026-09-23. Decision: **PROCEED_WITH_BOUNDED_CASE; CORE_EMPIRICAL_INPUTS_NOT_YET_READY**. This is a method judgment, not an empirical PASS or publication GO.

Routing: requested `gpt-6-astra / high`; separate reviewer task `/root/paper1_phase2_method` is observable. Parent-reported routing is Astra/high; independently exposed model/effort telemetry and tool-acceptance receipt: `NOT_OBSERVED`. No delegation, outcome computation, purchase, SCC access, commit or push by this reviewer.

Reviewed: Phase 2 prompt, research plan, assessment, accepted Phase 1 result/review, and the five specified engineering artifacts. Scope is the preferred **2023-01-24 NYSE opening-auction failure**. No viable backup was recorded in the supplied screen. Four COVID circuit-breaker rows are not four alternative channel-specific experiments; this screen establishes a defensible first case, not the best event across 2019–2025.

## 1. Economic object and selection

Retain January 24 on institutional grounds. The SEC order documents a systems-induced failure of opening auctions for 2,824 securities, while NYSE continuous trading began. Thus **the missing function is an opening price-setting mechanism, not the entire NYSE or cash market**. LULD pauses, short-sale restrictions and subsequent corrections are consequences of the incident. The SEC's 10:21 update disclosed the problem; it was not a common recovery time. At 10:53 its full scope was still being investigated. [SEC order, §§19–39](https://www.sec.gov/files/litigation/admin/2026/34-104934.pdf).

The feasible first estimand is a **case-level change in cross-tool consistency and adjustment during a disrupted cash opening, relative to predetermined normal openings**. Separate (i) same-stock redistribution across cash venues; (ii) the complete cash basket, SPY and traded ES contract. The latter is a substitution diagnostic, not proof that the same trader moved orders or that ETF/ES prices represent fundamental truth. A pure causal effect of auctions, DMMs, concentration or ETF availability is not identified by the package.

Exposure must use independently documented auction failure and pre-event basket weights. The 84 LULD securities are an endogenous consequence subgroup, not the exogenous treated population. Nonfailed NYSE or Nasdaq-listed securities can provide descriptive comparisons only after recognizing nonrandom assignment and spillovers; SPY and ES are potentially affected alternative channels, not untreated controls.

## 2. Necessary finite repairs before the main run

1. **Restore the approved baseline.** The initial manifest uses five pre-days, not the prompt's five before and five after. Use Jan 17–20, 23 and Jan 25–27, 30–31, subject to verified calendar/operator exclusions. Preserve scheduled-news days and flag/split overlapping windows unless an explicit pre-outcome amendment justifies replacing them. Later normal days are benchmarks, not measurements of predetermined exposure; estimate exposure/development choices from pre-event days only.
2. **Do not turn notice time into recovery.** Retrieve symbol-level pause/reopen and quote-validity states. A bounded initial 09:25–11:30 ET package is reasonable; 11:30 is a collection endpoint, not asserted recovery. Supplement initialization snapshots/last-valid state at 09:25 and previous-close anchors. If official status shows relevant reopening after 11:00, extend to 30 minutes after that documented boundary without consulting the price response; unresolved cases remain right-censored. Recover economic consistency separately with the prompt's normal-band/30-valid-second rule.
3. **Keep corrected and contemporaneous information distinct.** Final cancellations can clean transaction metrics, but must not erase the prices/messages participants actually saw. Label contemporaneous disseminated states, administratively invalid states and ex-post corrected trades. Quotes cleared by a halt/zero message are not stale executable quotes. A robust stock basket cannot silently carry all paused components or reweight missing constituents to 100%.

These are targeted implementation corrections, not a new whole-project freeze. Existing partial windows can test parsing and clocks now, but cannot estimate the opening disruption.

## 3. Minimum data and what can proceed independently

Core: historical complete S&P 500 membership/weights and adjusted prior-close anchors; consolidated constituent/SPY quotes, trades, venue identifiers and condition/correction state; independently identified auction-failure membership plus per-security halt/reopen records; actual ES contract quotes/trades/status; the event and ten fixed normal-day windows. End-of-day correction/reference files may be required even though market rows remain intraday-bounded. Status initialization must precede the first sampled second. Full MBO, exact PCF, all-year TAQ and every direct feed are **not** common prerequisites.

Cash venue activity needs venue-specific trade/quote records, not just a single NBBO stream. ETF–ES paths can run without the basket, explicitly labeled partial. Full three-tool claims require basket weight-coverage and halt-state accounting. National cash data need not include full depth for all metrics. Lack of participant time need not stop coarse paths if the actual common clock supports them; it does stop unsupported fine lead/lag claims.

Current receipts cover SPY/23 stocks at two venues and ES approximately 09:59–10:31 only. They lack the opening, full basket, consolidated venue/state coverage and matched baseline: **not enough for the core case**. SSH failure is an access issue, not evidence that licensed data do not exist. Historical market-wide data availability from Databento has not been established; do not substitute direct-feed BBO for it.

## 4. Contribution and inference boundary

- [Clark-Joseph, Ye & Zi (2017)](https://czi.finance/assets/DMM.pdf): source and relevant design sections verified; NYSE/EDGX disruptions establish a DMM/liquidity benchmark. Modern volume migration, wider spreads or newer dates alone add little.
- [Cespa & Foucault (2014)](https://academic.oup.com/rfs/article/27/6/1615/1596760): publisher abstract verified; cross-asset price learning already supplies a fragility mechanism. Theoretical novelty cannot be claimed here.
- [Box et al., intraday ETF/portfolio arbitrage](https://www.sciencedirect.com/science/article/pii/S0304405X21001537): existing repository reading retained; publisher access failed in this review, so no new method verification claimed. Ordinary ETF/basket lead–lag is already the relevant overlap.

The candidate increment is evidence on whether **cross-instrument consistency survives loss of the cash opening mechanism**, and whether alternative instruments adjust without an equivalent system-wide impairment. Divergence alone may reflect bad reference prices, corporate news, opening mechanics or cash-basket nonexecutability rather than lost information. Record timed news, compare normal openings and distinguish state coverage from economic divergence. Fit a common-price model only on valid stable support; no obligatory IS estimate across pauses. One event supplies one disruption, not thousands of independent shocks. Expansion is justified by distinctive interpretable evidence, not by a favorable ETF ranking.
