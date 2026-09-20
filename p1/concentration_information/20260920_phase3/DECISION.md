# Phase 3 decision: HOLD_DATA

Date: 2026-09-20. This is an executed-stage decision, not a research-plan memo.

## Decision

The new concentration-information project remains economically interesting, and the reported-weight network is usable for ranking financial connection. The present evidence does **not** support an identification or empirical-power judgment. The binding problems are event-clock breadth and executable quote support, not computation.

Do not buy more single-venue quote windows for the two current events. First obtain independent minute-stamped release evidence for at least four additional preselected events, including three AFTER_CLOSE events and at least one additional PRE_OPEN event, without using price responses to choose them. Then run the same pre-frozen common-mask diagnostic before any effect or power work.

## Gate table

| Component | Evidence | Decision |
|---|---|---|
| Reported-weight receiver network | PURE_D: 217 portfolios, 490 receivers and 3,912 issuer–receiver pairs. All 490 scores are distinct. PURE_D vs INDEX_BD Spearman is 0.9534. | **PASS for ranking/technical sample.** Unitless reported-weight connection, not dollar exposure or causal treatment. |
| Balanced receiver pilot | 10 HIGH/LOW pairs; size SMD 0.0119 and liquidity SMD 0.0058; all 10 retain HIGH>LOW under INDEX_BD. | **PASS for a 20-stock technical sample.** Continuous score remains primary; groups are display/diagnostic strata. |
| Event clock | 32 candidate 2023 release groups; zero are scientifically frozen. Two Exxon PRE_OPEN issuer-metadata clocks are conditional technical anchors only because first-public status is not independently certified. | **FAIL for six-event/cross-session pilot.** Same issuer and session cannot identify general propagation or establish event-cluster independence. |
| Four venue-specific BBO feeds | 45,582 actual BBO records across eight files. XNAS produces baseline-valid responses for only 6/20 and 5/20 receivers; ARCX 4/20 and 3/20; BATS and XNYS 0/20. | **FAIL common mask.** Missing venue state is UNKNOWN, not zero response. |
| Derived composite BBO | `EQUS.MINI` is documented as a multi-venue aggregated BBO, not full SIP NBBO. API history begins 2023-03-28, so January is unavailable; its July file begins 07:00 ET, after the 06:00 event, yielding 0/20 baselines. | **FAIL for current early-PRE events.** Do not relabel it SIP NBBO. |
| 20-observation trace audit | Each run checks 20 private SCC trace rows, while Git exports only aggregate status counts and a source-file hash. Many private rows intentionally have no source timestamp because no prior venue state existed. | **PASS as an aggregate missingness/provenance audit only.** It is not 20 valid endpoint reconstructions and cannot cure the common-mask failure. |
| 2023 Nasdaq-100 special rebalance | Official timing/rule and actual QQQ pre/post membership holdings are documented. Exact dated July 14 full pro-forma security weights are not. | **H3 BLOCKED.** Public secondary weight table is support evidence only, not an authoritative treatment vector. |
| Identification and power | Two conditional event dates, one issuer, one session; statistical independence is NOT_ESTABLISHED and there is no full receiver common mask. | **NOT ESTIMABLE.** No SE, p-value, MDE, or causal GO is reported. |

## Quote acquisition and cost

Nine native DBN files were purchased and retained only on SCC: four XNAS/BATS, four ARCX/XNYS, and one late-period `EQUS.MINI`. Exact quoted usage totals **USD 0.015124082565**; actual vendor billing remains to be reconciled. The files contain 45,891 decoded BBO records in total. The January composite request failed range validation before download and cost no time-series call.

Databento's BBO documentation states that no interval record is printed when neither a trade nor a BBO update occurs. Therefore sparse early-PRE rows cannot be interpreted as zero movement. Its dataset documentation describes `EQUS.MINI` as an aggregated multi-venue top-of-book product; it is not a documented SIP NBBO. See [schemas](https://databento.com/docs/knowledge-base) and [venues/datasets](https://databento.com/docs/venues-and-datasets).

## What the exploratory responses do not say

The only nonempty paired HIGH-minus-LOW summaries come from two XNAS same-industry pair-event rows per horizon. Positive fractions equal 0.5; all cross-industry common-valid counts are zero. These aggregates are retained to prove the code executed, but they are not evidence for direction, precision, mechanism, identification, or power.

## One next action

Construct and source-lock four more release clocks—three AFTER_CLOSE and one additional PRE_OPEN—from the already frozen 32-event calendar, using issuer/wire publication evidence that documents timestamp precision and first-public interpretation, with no response-based selection. Revalidate the two existing conditional anchors or replace them. Require six-event session diversity and a 20/20 common quote mask on a documented feed before buying a larger panel. If that fails, keep the project at daily-frequency market facts and drop the minute-price-discovery claim.
