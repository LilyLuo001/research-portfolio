# Price Discovery Hubs and Market Resilience: Substitution Across Stocks, ETFs, and Futures

## Draft status

Research manuscript draft, 23 September 2026. The research question, contribution boundary, main case, measurement system and a real-data engineering demonstration are complete. The 2015 NYSE event dataset and main estimates have not yet been assembled; sections reporting them are written as an executable empirical structure, not as fabricated findings.

## Abstract

Modern equity price discovery is concentrated in a small set of highly liquid securities and trading channels. Concentration can be benign if alternative channels immediately replace a temporarily impaired hub, or fragile if apparent liquidity depends on an irreplaceable venue. We study this distinction in the S&P 500 ecosystem, where index ETFs, index futures and a complete cash basket express closely related exposures. Our primary case is the 8 July 2015 NYSE/NYSE American technical incident, which removed the matching/connectivity capacity of two affiliated cash exchanges while NYSE Arca, other U.S. exchanges and the index ETF/futures complex remained potential substitutes. We distinguish absolute replacement activity from mechanical market-share reallocation and measure system consequences separately through normalized adjustment, cross-channel consistency and recovery. A real-data prototype on two FOMC event/control pairs demonstrates that the proposed activity and consistency measures are operational and economically distinct, but it is not evidence on channel loss. The final paper asks whether concentrated price discovery is replaceable—and thus resilient—or whether the loss of a hub causes a measurable system-level delay. This framing moves beyond average lead–lag rankings and connects ETF–stock price discovery to the buy side's concern that apparently diversified portfolios may rely on a narrow information and execution infrastructure.

## 1. Motivation

The U.S. equity market looks highly decentralized: hundreds of stocks, multiple exchanges, ETFs, futures and electronic market makers trade simultaneously. Economically, however, common information can enter through a much smaller set of instruments. S&P 500 risk is often expressed through ES or SPY before an investor trades hundreds of underlying securities. This concentration is not necessarily harmful. A hub can improve coordination and price efficiency when it is liquid, cheap and continuously available.

The unresolved issue is **replaceability**. Two markets can display the same normal-day leadership pattern while having very different resilience. In the first, traders shift seamlessly from an impaired venue or instrument to substitutes and the ecosystem keeps processing information. In the second, measured liquidity elsewhere survives but the system loses adjustment capacity or cross-instrument consistency. Average information shares and next-second prediction cannot distinguish these worlds.

This distinction is directly relevant to asset managers. A diversified stock portfolio can still depend on a concentrated price-discovery and execution architecture. If that architecture is replaceable, concentration mainly reflects efficiency. If it is not, a local operational failure can become a common source of stale prices, uncertain marks and execution risk. The question is therefore not whether ETFs are generically good or bad, nor whether “ETF leads stock” on average. It is whether a concentrated hub can be replaced without an economically important system loss.

## 2. Contribution

The proposed contribution is a linked measurement chain:

`pre-event channel dependence → documented capacity loss → absolute replacement by surviving channels → system adjustment and consistency → recovery`.

Each arrow is measured separately. A remaining venue's market share rises mechanically when another venue disappears, so relative share is never sufficient evidence of substitution. Replacement requires additional absolute updating/trading activity, and resilience additionally requires that system adjustment and cross-channel consistency do not deteriorate persistently.

The paper complements four literatures. ETF price-discovery studies establish dynamic leadership and the transmission of firm-specific information through ETFs. ETF-arbitrage studies relate funds to their portfolios. Market-fragility theory shows how cross-asset learning can transmit liquidity stress. Regulatory work on the 2015 NYSE suspension documents cash-volume migration and liquidity conditions. The paper must add evidence on the *same-index cross-asset ecology*: whether alternative cash venues, ETF and futures jointly replace the lost channel, and whether observed migration preserves price adjustment. If it only reproduces cash-volume migration or ordinary ETF/ES lead–lag, the contribution is insufficient.

## 3. Institutional setting and primary case

The preferred laboratory is the S&P 500 complex: SPY and related index ETFs, the active ES contract and a complete contemporaneous stock basket. These instruments are not identical securities. ETF cash, fees and holdings, futures carry and dividends, and index reconstitution must be respected. The design therefore compares properly normalized returns and, where input data permit, economically adjusted replication values.

On 8 July 2015, connectivity problems at NYSE and NYSE MKT escalated before a formal trading suspension. Regulatory evidence places gateway deterioration at about 10:45 ET, the formal suspension at 11:32, and reopening at 15:10. Other U.S. exchanges remained active and gained trading share. The event is attractive because two affiliated cash exchanges lost capacity during the common trading session while NYSE Arca, other cash venues and ES remained potential substitutes. The main estimand will focus on NYSE-listed S&P 500 securities, while simultaneous NYSE American impairment remains an explicit accompanying treatment rather than a control.

It is not a textbook randomized shock. Deterioration preceded the formal halt, public knowledge may have evolved, common news remained possible, and routing spillovers affected the alternatives. Accordingly, the empirical object is first a documented state transition. Other venues, ETF and futures are mechanism outcomes, not untreated units. Same-clock normal days provide descriptive baselines, not a claim that all confounding is removed.

## 4. Hypotheses

**H1: Replaceable concentration.** When NYSE capacity deteriorates and disappears, surviving cash venues and index instruments increase absolute updating activity. Cross-channel adjustment and consistency exhibit limited deterioration and recover promptly after reopening.

**H2: Dependent concentration.** Surviving channels gain mechanical share but fail to replace the lost absolute capacity. Normalized price adjustment or cross-channel consistency deteriorates materially and recovery is slow or incomplete.

**H3: Asymmetric replacement.** Replacement can preserve common-index price discovery while leaving some constituent-level information impaired. This extension requires a complete basket and security-level exposure; it is not inferred from the current 23-stock sample.

Both H1 and H2 are economically meaningful. The paper does not require an “ETF is harmful” conclusion. Stable substitution would show that visible concentration coexists with robust redundancy.

## 5. Data

The main case requires four synchronized blocks:

1. consolidated U.S. quotes and trades with venue, condition/correction fields, participant and SIP clocks where available, and explicit market states;
2. direct or auditable venue/status records distinguishing degradation, formal suspension and recovery;
3. SPY and the active ES contract with quote/trade and contract/session metadata;
4. point-in-time S&P 500 membership and either historical SPY holdings/PCF economics or a clearly labeled complete fixed-weight return proxy.

Raw and licensed row-level data remain on SCC. The repository stores code, public event metadata, aggregate outputs and receipts. Existing SCC data cover 2023–2024 FOMC windows for SPY, 23 stocks and ES on selected venues. They do not cover the full 2015 event ecology and cannot be silently substituted for it.

## 6. Measurement

### 6.1 Channel activity

For each fixed channel we measure valid midpoint revisions, quote/trade activity, displayed spread and displayed top-of-book depth in absolute units. Relative shares are secondary and always shown with absolute counts and a fixed tool universe. An unavailable channel is not represented by a carried stale quote.

### 6.2 Adjustment paths

Each tool's midpoint is normalized to a pre-event anchor and expressed as a log-return path in basis points. The complete basket uses fixed, point-in-time quantities or weights. ES uses an actual dated contract. Fixed endpoints summarize adjustment but no later price is treated as fundamental truth.

### 6.3 Consistency and recovery

Cross-channel divergence is measured from a fixed pre-event relation. In the full study, financing/dividend/carry and ETF cash items are incorporated when the data permit. Divergence levels and areas are computed only over jointly valid support. Recovery requires a predeclared threshold and a sustained valid interval after official reopening; non-recovery is right-censored rather than assigned the window endpoint.

### 6.4 Model boundary

The primary design is deliberately non-structural. A common-price VECM/Hasbrouck information-share extension is allowed only after the economic mappings, longer development windows, cointegration rank, residual behavior and correlated-innovation ordering sensitivity are verified. The short event window does not support searching across multiple structural models.

## 7. Empirical design

The event timeline separates pre-degradation, degradation, formal halt and post-reopening states. The main plots show absolute activity by channel alongside system adjustment and divergence. Pre-specified same-clock normal days are selected without using returns or volatility. Results are reported event-by-event; millions of ticks do not create millions of independent shocks.

The central empirical test is a joint classification:

- **replacement with resilience:** surviving-channel absolute activity rises and system loss is small/transitory;
- **replacement with strain:** activity migrates but divergence or adjustment loss persists;
- **no effective replacement:** absolute activity does not compensate and system loss is material;
- **no detectable loss:** the channel disappears without a measurable activity or consistency cost.

Security-level venue exposure can describe heterogeneous responses, but it does not turn alternative channels into untreated controls. With only one qualifying incident, uncertainty is presented through event-level paths, measurement sensitivities and matched-day variation rather than pseudo-precise tick-level p-values.

## 8. Phase 1 evidence

The Phase 1 prototype uses the first two chronological 2023 FOMC event/control pairs already on SCC. The fixed instruments are SPY XNAS BBO and front ES GLBX BBO; the fixed sensitivity shifts the one-second grid by 500 ms.

Both FOMC events produce rapid, broadly aligned 60-second moves and much higher midpoint updating than their controls. On 1 February, SPY and ES move roughly −25 bp at the integer grid and the 60-second residual divergence is below its first-ten-second peak. On 22 March, both move roughly +45 bp, but residual divergence grows after the early peak. The grid shift preserves that qualitative contrast.

This is useful because adjustment activity and cross-channel consistency are empirically distinct even in a common-news setting. It also cautions against calling co-movement “successful price discovery.” The prototype does not contain a channel loss, national NBBO, complete cash basket or carry correction. It therefore validates the measurement pipeline but offers no conclusion on H1 or H2.

## 9. Planned exhibits

- Table 1: incident chronology, affected capacity, public information and alternative-channel status.
- Figure 1: fixed channel map and data coverage.
- Figure 2: absolute channel activity through degradation, halt and reopening.
- Figure 3: normalized ETF, ES and complete-basket paths with jointly valid support.
- Figure 4: divergence and recovery, with matched-day envelopes.
- Table 2: replacement/system-loss classification and measurement sensitivity.
- Appendix: clocks, conditions, missing states, basket construction, contract mapping and event exclusions.

## 10. Interpretation and limitations

The case can establish what the ecology did during a documented venue-capacity loss. It cannot by itself estimate a universal causal effect of concentration. Technical origin does not eliminate anticipation, market-wide news or routing spillovers. National quotation and complete-basket construction are essential because a venue outage is otherwise confounded with data absence. The paper will not call share migration information transfer, quote convergence fundamental efficiency, or a one-second correlation a permanent information share.

If the complete event package reveals strong replacement and little system loss, the finding is a resilient-market result: concentrated hubs are backed by substitutes. If activity migrates but the system degrades, the contribution is a distinction between volume redundancy and information resilience. If the case adds nothing beyond the SEC's cash-market evidence, the project should be archived as a measurement replication rather than enlarged through outcome-selected events.

## 11. Current completion state

The paper's question, nearest-neighbor boundary, primary case, hypotheses, measurements, code and real-data prototype are written and versioned. The main 2015 event analysis remains unestimated because the nationwide 2015 event data, exact venue/status chronology and complete contemporaneous basket are not currently verified on SCC. `phase1/NEXT_ACTION.md` specifies one acquisition/staging action to reach the first paper-level empirical result.
