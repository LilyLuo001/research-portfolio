# Price Discovery Hubs and Market Resilience: Substitution Across Stocks, ETFs, and Futures

## Draft status

Research manuscript draft, updated 23 September 2026. The contemporary primary case, fixed 503-security basket, ten reference sessions and cross-tool result are now complete. The selected event is the 24 January 2023 NYSE opening-auction failure. The earlier 2015 case is an optional external-validity comparison, not the main result or a prerequisite. Detailed receipts, aggregates and figures are in [Phase 2](phase2/RESULTS.md).

## Abstract

Modern equity price discovery is concentrated in a small set of highly liquid securities and trading channels. Concentration can be benign if alternative tools preserve a common price when a hub fails, even when they do not replace its transaction capacity. We study this distinction in the S&P 500 ecosystem using the 24 January 2023 NYSE opening-auction failure, when 2,824 NYSE-listed securities did not receive their scheduled opening auctions. For 503 contemporaneous S&P 500 security issues, SPY and the active E-mini contract, we distinguish absolute replacement activity from mechanical market-share reallocation and measure cross-tool consistency against five pre- and five post-event sessions. In the saved 0-through-300-second window, named-feed NYSE-listed trade notional was only 35.8% of its normal median; XNAS and ARCX gained share but their combined absolute notional was 95.1% of its own normal level. Nevertheless, SPY and ESH3 stayed inside their normal opening consistency band. The frozen cash basket records three isolated exceedances, but independent decomposition shows each is caused by one crossed-composite constituent exclusion rather than a broad price dislocation. The evidence separates execution redundancy from information resilience: the missing auction volume was not replaced, but common index pricing remained coherent. This result connects ETF–stock price discovery to the buy side's concern that apparently diversified portfolios may rely on a narrow execution architecture without necessarily sharing the same fragility in common-information processing.

## 1. Motivation

The U.S. equity market looks highly decentralized: hundreds of stocks, multiple exchanges, ETFs, futures and electronic market makers trade simultaneously. Economically, however, common information can enter through a much smaller set of instruments. S&P 500 risk is often expressed through ES or SPY before an investor trades hundreds of underlying securities. This concentration is not necessarily harmful. A hub can improve coordination and price efficiency when it is liquid, cheap and continuously available.

The unresolved issue is **replaceability**. Two markets can display the same normal-day leadership pattern while having very different resilience. In the first, traders shift seamlessly from an impaired venue or instrument to substitutes and the ecosystem keeps processing information. In the second, measured liquidity elsewhere survives but the system loses adjustment capacity or cross-instrument consistency. Average information shares and next-second prediction cannot distinguish these worlds.

This distinction is directly relevant to asset managers. A diversified stock portfolio can still depend on a concentrated price-discovery and execution architecture. If that architecture is replaceable, concentration mainly reflects efficiency. If it is not, a local operational failure can become a common source of stale prices, uncertain marks and execution risk. The question is therefore not whether ETFs are generically good or bad, nor whether “ETF leads stock” on average. It is whether a concentrated hub can be replaced without an economically important system loss.

## 2. Contribution

The proposed contribution is a linked measurement chain:

`pre-event channel dependence → documented capacity loss → absolute replacement by surviving channels → system adjustment and consistency → recovery`.

Each arrow is measured separately. A remaining venue's market share rises mechanically when another venue disappears, so relative share is never sufficient evidence of substitution. Replacement requires additional absolute updating/trading activity, and resilience additionally requires that system adjustment and cross-channel consistency do not deteriorate persistently.

The paper complements four literatures. ETF price-discovery studies establish dynamic leadership and the transmission of information through funds. ETF-arbitrage studies relate funds to their portfolios. Market-fragility theory shows how cross-asset learning can transmit liquidity stress. Exchange-incident studies document cash-volume migration and liquidity conditions. The incremental object is the *same-index cross-asset ecology*: whether alternative cash venues, ETF and futures replace lost activity, and whether price consistency can survive even when activity does not. The 2023 result is not ordinary ETF/ES lead–lag and not a replication of cash market-share migration because it compares absolute channel levels with a separate system-output measure.

## 3. Institutional setting and primary case

The preferred laboratory is the S&P 500 complex: SPY and related index ETFs, the active ES contract and a complete contemporaneous stock basket. These instruments are not identical securities. ETF cash, fees and holdings, futures carry and dividends, and index reconstitution must be respected. The design therefore compares properly normalized returns and, where input data permit, economically adjusted replication values.

On 24 January 2023, a NYSE systems error caused the exchange to skip scheduled opening auctions for 2,824 NYSE-listed securities. The SEC reports that 84 securities subsequently entered LULD pauses and more than 4,000 trades were ultimately busted. This was an opening price-setting mechanism failure, not a closure of the NYSE or the cash market. Continuous trading, other cash venues, SPY and ESH3 remained active, which makes the event a direct test of whether the surrounding ecology preserved a common price despite the missing auction.

It is not a textbook randomized shock. The alternatives are affected substitute channels rather than untreated units, routing spillovers are part of the mechanism, and Databento marks the event-day XNYS.PILLAR feed as degraded. The empirical object is therefore a documented state transition anchored in the SEC order. Same-clock normal days provide descriptive baselines, not a claim that every confounder is removed.

## 4. Hypotheses

**H1: Replaceable concentration.** When the NYSE opening-auction mechanism fails, surviving cash venues and index instruments increase absolute updating activity. Cross-channel adjustment and consistency exhibit limited deterioration and recover promptly during continuous trading.

**H2: Dependent concentration.** Surviving channels gain mechanical share but fail to replace the lost absolute capacity. Normalized price adjustment or cross-channel consistency deteriorates materially and recovery is slow or incomplete.

**H3: Asymmetric replacement.** Replacement can preserve common-index price discovery while leaving some constituent-level information impaired. This extension requires a complete basket and security-level exposure; it is not inferred from the current 23-stock sample.

Both H1 and H2 are economically meaningful. The paper does not require an “ETF is harmful” conclusion. Stable substitution would show that visible concentration coexists with robust redundancy.

## 5. Data

The main case requires four synchronized blocks:

1. consolidated U.S. quotes and trades with venue, condition/correction fields, participant and SIP clocks where available, and explicit market states;
2. direct or auditable venue/status records distinguishing the failed auction, continuous-trading state, pauses/reopens and later administrative correction;
3. SPY and the active ES contract with quote/trade and contract/session metadata;
4. point-in-time S&P 500 membership and either historical SPY holdings/PCF economics or a clearly labeled complete fixed-weight return proxy.

Raw and licensed row-level data remain on SCC. The repository stores code, public event metadata, aggregate outputs, figures and receipts. The completed package contains eleven 09:25–11:30 ET sessions from XNYS.PILLAR, XNAS.ITCH, ARCX.PILLAR and GLBX.MDP3. The cash quote construct is explicitly a three-direct-feed composite BBO, not SIP NBBO or complete NMS coverage. Historical CRSP membership supplies 503 security issues and prior-close capitalization-proxy weights; these are not official float-adjusted S&P weights.

## 6. Measurement

### 6.1 Channel activity

For each fixed channel we measure valid midpoint revisions, quote/trade activity, displayed spread and displayed top-of-book depth in absolute units. Relative shares are secondary and always shown with absolute counts and a fixed tool universe. An unavailable channel is not represented by a carried stale quote.

### 6.2 Adjustment paths

Each tool's midpoint is normalized to a pre-event anchor and expressed as a log-return path in basis points. The complete basket uses fixed, point-in-time quantities or weights. ES uses an actual dated contract. Fixed endpoints summarize adjustment but no later price is treated as fundamental truth.

### 6.3 Consistency and recovery

Cross-channel divergence is measured from a fixed pre-event relation. In the full study, financing/dividend/carry and ETF cash items are incorporated when the data permit. Divergence levels and areas are computed only over jointly valid support. Recovery requires a predeclared threshold and a sustained valid interval after a documented marker; non-recovery is right-censored rather than assigned the window endpoint.

### 6.4 Model boundary

The primary design is deliberately non-structural. A common-price VECM/Hasbrouck information-share extension is allowed only after the economic mappings, longer development windows, cointegration rank, residual behavior and correlated-innovation ordering sensitivity are verified. The short event window does not support searching across multiple structural models.

## 7. Empirical design

The event timeline separates the pre-open state, missing 09:30 auction, continuous trading, NYSE's internal discovery, member disclosure and continuing scope investigation. The main plots show absolute activity by channel alongside system adjustment and divergence. Pre-specified same-clock normal days are selected without using returns or volatility. Results are reported event-by-event; millions of ticks do not create millions of independent shocks.

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
- Figure 2: absolute channel activity around the failed auction and subsequent continuous-trading intervals.
- Figure 3: normalized ETF, ES and complete-basket paths with jointly valid support.
- Figure 4: divergence and recovery, with matched-day envelopes.
- Table 2: replacement/system-loss classification and measurement sensitivity.
- Appendix: clocks, conditions, missing states, basket construction, contract mapping and event exclusions.

## 9A. Contemporary-case result

The opening-auction failure sharply reduced the level of opening activity without producing a comparably large loss of common-price consistency. For NYSE-listed basket securities in the saved 0-through-300-second window (301 integer buckets, including 09:35:00), XNYS trade notional was 27.1% of its ten-session median. XNAS plus ARCX rose from 13.3% to 35.7% of the three named feeds' notional, but their combined absolute notional was only 95.1% of normal. Across all three feeds, opening notional was 35.8% of normal. The share shift therefore overstates economic replacement.

The price-output evidence is different. SPY–ESH3 did not exceed its same-clock normal band in the first 60 seconds. The frozen cash basket exceeded the basket–SPY and basket–ESH3 bands at seconds 4, 30 and 31, but raw-feed decomposition attributes each exceedance to one crossed-composite constituent being excluded under the no-renormalization rule (MMM, then CVS), not to a broad basket move. Carrying that single name from the immediately preceding valid second puts each gap inside the normal band. Five-minute deviation-area ranks were 4th, 3rd and 4th of eleven from smallest to largest for basket–SPY, basket–ESH3 and SPY–ESH3; none was an extreme tail event. The appropriate classification is incomplete activity substitution with common-price resilience, subject to the direct-feed basket measurement limitation.

This finding does not establish that ETFs caused resilience or preserved firm-specific information. It shows that common-index price coherence can survive the disappearance of a high-volume price-setting mechanism even when the missing transaction capacity is not replaced. That separation is the paper's empirical contribution.

## 10. Interpretation and limitations

The case can establish what the ecology did during a documented venue-capacity loss. It cannot by itself estimate a universal causal effect of concentration. Technical origin does not eliminate anticipation, market-wide news or routing spillovers. National quotation and complete-basket construction are essential because a venue outage is otherwise confounded with data absence. The paper will not call share migration information transfer, quote convergence fundamental efficiency, or a one-second correlation a permanent information share.

If the complete event package reveals strong replacement and little system loss, the finding is a resilient-market result: concentrated hubs are backed by substitutes. If activity migrates but the system degrades, the contribution is a distinction between volume redundancy and information resilience. If the case adds nothing beyond the SEC's cash-market evidence, the project should be archived as a measurement replication rather than enlarged through outcome-selected events.

## 11. Current completion state

The paper's question, contemporary case, event package, code, aggregate results and figures are complete. The bounded independent numerical review is the remaining Phase 2 verification step. After that review, manuscript work should center the activity-versus-consistency separation. A second event may be added as external-validity evidence, but it is not needed to decide whether the present case contains a distinctive result and must not be chosen because its sign is more favorable.
