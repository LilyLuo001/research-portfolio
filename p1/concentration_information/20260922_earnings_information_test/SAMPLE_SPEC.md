# Earnings information test: fixed sample specification

The sampling frame is the 23-stock panel actually used by the completed ordinary-day and FOMC models. `BF` appears in an inherited safe roster but never entered the feature panel and remains excluded. Sorting the inherited report weights in descending order, with the stable symbol as the tie-break, fixes ranks 1, 5, 9, 14, 18 and 23 as **AAPL, LLY, CVS, CMI, EBAY and NWSA**. The inherited weights stratify this bounded pilot; they are not contemporaneous holdings or treatment variables.

For each issuer in 2023 and 2024, the first four regular quarterly/annual result releases by economic date are retained. Duplicate annual and quarterly metadata rows for the same release are one event. Candidate dates and times come from the existing SCC I/B/E/S actuals metadata projection (`anndats`, `anntims`) without reading EPS values. Issuer IR releases or original filings are the preferred public-clock authority. Where no primary source establishes the first-public second, the event remains usable at the coarser recorded minute but is labelled `CLOCK_CANDIDATE`, not falsely upgraded to a microsecond clock.

The chronological folds are global: January-June 2023 `TRAIN`, July-September 2023 `VALID`, October-December 2023 `HISTORY`, and all of 2024 `TEST`. Each event is paired with the fifth prior NYSE full trading session at the same New York clock time. Event and control remain in the same fold. Selection and controls use no price response.

The requested raw window is ten minutes before through sixteen minutes after each event/control anchor. XNAS.ITCH and ARCX.PILLAR request the fixed 23 stocks plus SPY; GLBX.MDP3 requests `ES.v.0`. These are venue-native BBO/trade feeds, not SIP NBBO. Raw data, row-level features, fits and predictions remain on SCC.

The primary estimand is the issuer-stock next-second prediction gain from A2 to A5 on common target support. A2 contains baseline quote/ES information and cash-stock trades; A5 additionally contains SPY quotes and SPY trades. The result is conditional predictive content, not a structural information share or a causal ETF leadership coefficient.
