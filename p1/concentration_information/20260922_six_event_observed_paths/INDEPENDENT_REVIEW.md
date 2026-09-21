# Independent review

## Final judgment

**Usable for descriptive venue-specific paths, with one partial tail; not usable for price-discovery inference.** I independently decoded the raw SCC DBNs for all six fixed events, seven clock variants, both feeds, and both symbols. After the corrections listed below, every available baseline, +5, and +60 quote and derived value in `ENDPOINTS.csv` matches the independent reconstruction exactly. The July XOM 06:30 ET variant is available through +45 minutes but its +60 target is outside both source archives and is correctly unavailable.

The data show several movements outside the contemporaneous cross-spread bounds and broadly similar venue directions, especially for January XOM, both AAPL dates, and the MSFT notice window. That is enough to establish that the selected venue BBO paths can be described. It does not compare the same cash flow, identify release causality, or show that an issuer led SPY in price discovery. The revised next action in `RESULTS.md`—a bounded, predeclared same-component pilot using a lagged-report rest-of-SPY basket and ETF-implied issuer component—is supported, provided it reports tracking error and remains explicitly a retrospective proxy rather than an event-time holdings claim.

Requested reviewer routing was `gpt-5.6-sol / high`; backend routing telemetry was not visible. Actual routing: **`NOT_OBSERVED`**.

## Independent raw recomputation

I used a separate SCC decoder, not the delivered CSVs. It resolved date-valid instrument IDs from each DBN's metadata, retained the full BBO state sequence, grouped by instrument and publisher, classified undefined/zero-sided/crossed states, detected conflicting states at equal `ts_recv`, and selected the latest state at or before each target. Every file had exactly one relevant publisher: publisher 2 for XNAS and publisher 43 for ARCX. Across the selected SPY/issuer records in all 12 source files, every raw BBO classified valid and there were zero conflicting same-timestamp states. Thus the state-aware rule is correct but does not alter the available reviewed endpoints in this sample.

The table reports independent midpoint baselines and changes. “NA” is a coverage result, not a zero return.

| Event / anchor | Feed | SPY baseline | SPY +5 bp | SPY +60 bp | Issuer baseline | Issuer +5 bp | Issuer +60 bp |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| XOM 2023-01-31 06:30 | XNAS | 398.620 | -8.6549 | +27.4698 | 112.360 | -241.1890 | -44.0548 |
| XOM 2023-01-31 06:30 | ARCX | 398.630 | -9.0309 | +27.3437 | 112.300 | -222.1728 | -40.9617 |
| XOM 2023-07-28 06:00 | XNAS | 454.605 | -3.5195 | -2.4197 | 105.775 | 0.0000 | -155.5188 |
| XOM 2023-07-28 06:00 | ARCX | 454.600 | -3.1896 | -2.1997 | 105.830 | +5.6695 | -144.0990 |
| XOM 2023-07-28 06:30 | XNAS | 454.430 | -5.8315 | NA | 105.830 | -108.1924 | NA |
| XOM 2023-07-28 06:30 | ARCX | 454.435 | -5.7214 | NA | 105.830 | -10.8665 | NA |
| UNH 2023-04-14 05:55 | XNAS | 412.790 | +1.4535 | +3.2704 | 529.500 | +75.5430 | -10.2927 |
| UNH 2023-04-14 05:55 | ARCX | 412.780 | +1.6958 | +3.5128 | 527.070 | +103.0224 | +38.3251 |
| AAPL 2023-02-02 16:30 | XNAS | 414.895 | -31.6948 | -17.7153 | 151.275 | -471.6576 | -391.6708 |
| AAPL 2023-02-02 16:30 | ARCX | 414.890 | -31.9362 | -20.1258 | 151.420 | -479.7913 | -396.9093 |
| AAPL 2023-08-03 16:30 | XNAS | 450.505 | -16.4260 | -31.9641 | 193.645 | -156.4719 | -335.4076 |
| AAPL 2023-08-03 16:30 | ARCX | 450.510 | -16.3148 | -31.6308 | 193.660 | -160.0744 | -340.8035 |
| MSFT notice 2023-04-25 16:07 | XNAS | 406.715 | +18.3175 | +23.1120 | 287.000 | +45.2962 | +62.3693 |
| MSFT notice 2023-04-25 16:07 | ARCX | 406.720 | +18.1943 | +23.3576 | 287.095 | +41.1014 | +58.1689 |

For all available rows, independent baseline mids, endpoint bids/asks/mids, quote ages, midpoint changes, and cross-spread bounds equal the delivered values; the maximum absolute numerical difference is **0.0**. There are 52 available symbol/feed/horizon cells and four unavailable cells: SPY and XOM at +60 for the July 06:30 variant on XNAS and ARCX.

## Time, coverage, labels, and event count

The historical conversions are correct: January 31 and February 2 use EST (UTC-5), while April 14, April 25, July 28, and August 3 use EDT (UTC-4). Therefore the UTC anchors 11:30, 21:30, 09:55, 20:07, 10:00/10:30, and 20:30 are correct. Event IDs were not used to infer dates.

The July source conflict is correctly one July 28 event with two retained anchors, not two events. The MSFT 16:07 ET anchor is correctly labeled an **availability notice, not a verified original release** in the event summary, result text, receipt, and final figure. The deliverable counts are six events, four issuers, six dates, and seven clock variants; venues and horizons are not counted as independent events.

Both July DBNs end at 11:15:59 UTC. An earlier output incorrectly carried the July 06:30 variant to +60; this affected four +60 cells and the final 30 path minutes (+46 through +75), not any +5 result. The reconstruction now marks those cells `UNAVAILABLE_BEYOND_ARCHIVE_END`, and the figure stops that panel after +45.

## Spread and venue diagnostics

The cross-spread interval is implemented correctly as `bid_end / ask_base - 1` to `ask_end / bid_base - 1`, in basis points. It is a quote-based diagnostic, not a confidence or executable-return interval.

- January XOM, both AAPL events, and the MSFT notice have issuer +5 intervals that exclude zero on both venues, with matching midpoint directions.
- July XOM at 06:00 has +5 issuer intervals crossing zero on both venues; XNAS is exactly flat while ARCX is +5.67 bp.
- July XOM at 06:30 is -108.19 bp on XNAS with a negative interval, but only -10.87 bp on ARCX with a wide interval crossing zero. The clock conflict and venue spread therefore materially limit a short-window claim.
- UNH +5 is positive on both venues, but the wide XNAS issuer interval crosses zero; both venue +60 issuer intervals cross zero and their midpoint signs differ.
- SPY +5 cross-spread intervals exclude zero in all seven variants. This does not make SPY movement attributable to the issuer announcement.

`EVENT_SUMMARY.csv` now records the primary interval-zero and cross-venue direction diagnostics explicitly for each event/variant.

## Static report-weight diagnostic

Independent CRSP queries reproduce the reported `percent_tna` and effective dates: XOM 1.4099998474% (2022-12-31 report), XOM 1.1699991226% (2023-06-30), UNH 1.2899999619% and MSFT 6.25% (2023-03-31), and AAPL 6.0499992371% / 7.7199974060% (2022-12-31 / 2023-06-30). The event-summary products equal report weight times the XNAS +5 issuer change. The corrected July 06:30 XOM value is **-1.265850 bp**, not -1.266844 bp. These are retrospective scale illustrations, not event-time contributions or causal residuals.

## Figure, files, and cost receipt

`PATHS.csv` has exactly 637 unique rows: 7 variants × 91 minute targets. A prior loop-indentation error wrote every path twice and caused a spurious diagonal between duplicate series; the corrected figure uses the unique rows, includes common-mid-baseline bid/ask bands, shows the July archive cutoff, and labels the MSFT panel as an availability notice. Visual inspection is consistent with the final path file.

The download receipt has eight unique successful requests, all scoped to SPY plus the listed issuer on XNAS or ARCX. Their quoted costs sum exactly to **$0.015461146832**; the files total 1,337,819 bytes and remained on SCC. The execution receipt records the same quote-based download total. A separate billing-ledger debit was not available, so the review does not independently claim an “actual charged” amount.

## Corrections made during review

1. Stopped July 06:30 paths at the raw archive end and made four +60 cells unavailable.
2. Removed duplicated path rows and the resulting figure diagonals.
3. Added the MSFT availability-notice label to the figure and result text.
4. Removed an unsupported claim that synthetic tests were delivered; actual raw-state findings are reported instead.
5. Corrected stale continuity wording: carried states retain their status and report age; continuity is not separately certified.
6. Corrected the static-weight arithmetic and added interval/venue diagnostics to `EVENT_SUMMARY.csv`.
7. Clarified that the recorded purchase amount is the sum of successful requests' pre-download cost quotes; no independent billing ledger was observed.

No commit or push was performed by the independent reviewer.
