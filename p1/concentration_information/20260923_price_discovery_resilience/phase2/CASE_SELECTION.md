# Phase 2 case selection

Date: 2026-09-23. Selected case: **NYSE_OPEN_20230124**. Status: `CASE_SELECTED / PREPARE_AND_STAGE_CORE_INPUTS`. Selection is based on institutional facts and the stated estimand, not newly computed event responses. Historical event-date outcomes were used elsewhere in P1; this case is therefore exploratory, not an untouched confirmatory sample.

## Decision

Select the 2023-01-24 NYSE opening-auction failure as the first contemporary case of **cash-opening mechanism disruption and cross-instrument resilience**. Do not label it a full NYSE outage. The documented operating error offers an identifiable missing market function; alternative cash venues, SPY and ES provide potentially observable substitute channels, subject to actual status verification. [Institutional evidence](https://www.sec.gov/files/litigation/admin/2026/34-104934.pdf).

The narrow question is: relative to normal openings, how did valid cash-basket, ETF and futures prices adjust, where did activity relocate, and how long did observable cross-tool inconsistency persist? It is not yet a causal test of concentration or proof of which tool knew fundamental value.

No backup is selected. The supplied table contains four 2020 market-wide circuit-breaker dates whose mechanisms do not supply the required channel-specific comparison. This is a bounded first-case selection, not a complete ranking of contemporary disruptions. Do not switch because responses are small, mixed or contrary to the narrative. A necessary-input failure should yield the precise core package gap, not an automatic return to 2015.

## Operational handoff

The independent review in `METHOD_REVIEW.md` supersedes three provisional choices in the initial engineering manifest:

- Restore five pre- and five post-event reference sessions: 2023-01-17, 18, 19, 20, 23; 25, 26, 27, 30, 31. Verify scheduled closures/operating incidents. News is a flagged condition, not automatic result-based exclusion.
- Use a bounded initial 09:25–11:30 ET window with valid start-state snapshots and prior-close basket anchors. Extend only for a documented operational boundary, otherwise report censoring. The 10:21 disclosure is not recovery.
- Define exposure from the actual auction-failure roster intersected with historical basket membership, retaining failed/nonfailed/unknown states. LULD status is a consequence stratum, not treatment assignment.

First executable sequence: align manifest to these finite corrections; verify/stage existing SCC paths and historical reference inputs; retrieve the precisely missing market/status windows; produce state/coverage and partial ETF–ES paths, then the complete-basket comparison when supported. No new methodological review or broad search is required to start that sequence.

Receipt-backed 09:59–10:31 two-venue/23-stock and ES segments remain useful engineering inputs but cannot stand in for the opening experiment. Restricted source permission, data absence and connection failure must remain separate statuses. If market-wide data require a supplier/account not presently configured, give one concrete delivery request and continue runnable partial work.

Final-case inference remains descriptive unless stronger comparison assumptions are substantiated. Method selection is not an empirical PASS, and no claim of novelty, substitution success or failure has been certified.

Reviewer routing: requested `gpt-6-astra / high`; actual separate task `/root/paper1_phase2_method`; independent backend telemetry `NOT_OBSERVED`. No empirical outcomes were opened by this reviewer.
