# Scientific decision at this execution checkpoint

**HOLD_DATA + HOLD_MEASUREMENT. The proposed scientific test is not yet executable; it has not rejected or supported the hypothesis.**

The useful result is a sharper boundary, not a null effect: existing acquired ETF quotes, monthly fund holdings, and public announcement timestamps are three different ingredients, and none can stand in for the other two. More observations from the same mismatched sources would not produce a trustworthy answer to “ETF versus actual basket, after the same company news.”

## What is now established

1. Corrected SCC extraction covers the original eight companies' 32 events using 2022–2023 monthly holdings. SPY report-level ticker-group membership is 32/32 and QQQ 16/32. Both have a prior-or-same-date report for every event. The earlier January gap was an extraction-window artifact, not missing holdings history. These are not independently verified event-time fund baskets or Top/Rest classifications.
2. Six fixed technical probes have source timestamps in premarket (3) or after-hours (3); none supplies an RTH technical probe. XOM July's 30-minute conflict must remain visible, and Microsoft's results-available notice is not a first-release timestamp. This does not establish that the full 32-event inventory has no RTH events.
3. An exact 29-file, 20,293,836-byte existing-data manifest was checked and a reviewed boolean-only SCC projection ran successfully, producing 456 file-source cells with no skipped files. See `QUOTE_SUPPORT_TABLE.csv` for endpoint diagnostics. No cell count is an effective sample size, and no single-venue dataset is called national NBBO.
4. The numerical implementation defect was repaired and independently tested. Empirical dependence calibration, denominator strength and economically justified exclusion margins remain unestablished; passing numerical fixtures does not supply them.

## What cannot be claimed

No estimate, p-value, MDE, empirical power, equivalence finding or causal conclusion was generated. The primary release guard still blocks response reads. An ETF price paired with a monthly approximate basket is not the approved contemporaneous-basket test; an earnings release timestamp without a matched historically available signal is not the standardized news-response design. The eight large issuers cannot support a claim about the long tail simply by being split into two groups.

## One next action

Produce a **single event-level basket-and-news admissibility packet for SPY**, starting from the existing inventory without selecting on returns: historical dated actual fund positions and per-share units/cash/actions, their relevance to the event-time basket, a defensible public-release interval, and the matched historically available news signal with units/revisions explained. If exact event holdings cannot be recovered, explicitly amend the question to a frozen lagged-holdings proxy study and assess its distinct contribution before opening responses; do not silently call it the actual basket.

Only after that packet demonstrates a measurable target should missing constituent/ETF quote windows be purchased automatically within the verified credits, as the user authorized. A quote order cannot repair absent fund-position or historical-news provenance. This is a bounded measurement decision, not a new whole-project feasibility audit and not permission to revive MF–ETF conversion or the old H2 result.
