# Source and engineering notes — bounded Phase 1 contribution

## Scope and search record

I searched only official operator/regulator materials for discrete 2015–2025 availability events, with a cap of six detailed candidates. The sources retained in `EVENT_CANDIDATES.csv` are: SEC material on the 2015 NYSE suspension; Deutsche Börse/Xetra Newsboard notices; Euronext's operator market-status record for 19 October 2020; and Nasdaq's historical Reg SCI notice for ISE Mercury. Four actual incidents were documented; no filler event was added. Inclusion is based on sourceable operational occurrence and timing, not price, return, volume, or any empirical response.

The only candidate presently retained for a U.S. venue-specific case design is `NYSE_2015_07_08`. The SEC's [public analysis](https://www.sec.gov/files/marketstructure/research/sec_data_highlight_2016-01.pdf), pp. 1 and 4, identifies the formal halt as 11:32–15:10 ET and says activity shifted to other exchanges; its [enforcement order](https://www.sec.gov/file/33-10463pdf), p. 4 ¶¶8–12, separately documents gateway degradation from about 10:45 and self-help/routing changes. Therefore formal-halt-only treatment would be misspecified. The event remains a **case candidate**, not an exogenous shock and not a causal result.

The other documented incidents are intentionally excluded pending their stated scope/clock defects. Euronext 2020 is especially useful as a negative design lesson: its own notice says cash and derivatives were jointly halted and later closing trades were cancelled/corrected. It is not legitimate to describe a vendor's stale close as a market halt or to manufacture a clean unaffected counterfactual.

## Existing FOMC engineering: accurate entry points

Metadata was read only from the named FOMC receipts, and code was inspected only in the FOMC `code/` directory. No SCC connection, DBN decode, feature read, result read, or calculation was performed.

| Function | Repository entry point | SCC location / input | Reusable fields and boundary |
|---|---|---|---|
| Manifest logic | `p1/concentration_information/20260922_fomc_information_arrival/code/build_fomc_manifests.py` | Manifest defines 13:44–14:11 ET source window and 13:50–14:10 analysis interval | 24 equity symbols (SPY + 23 stocks); 16 events and 16 fixed controls. The selection is historical/observed, not a new confirmation sample. |
| Native data/reuse check | `code/scc_fomc_quote_download.py` | `/project/econdept/qluo/bidirectional_information_20260922/fomc_information_arrival_20260922/raw/` | `mbp-1`, `XNAS.ITCH`, `ARCX.PILLAR`, `GLBX.MDP3`; raw paths and resolved ES contract are recorded in `results/DOWNLOAD_RECEIPT.json`. The script's `download` mode must not be used here. |
| Equity feature adapter | `code/scc_build_fomc_features.py` | Feature output recorded as `features/DIRECTIONAL_FEATURES_FOMC.parquet` under the same SCC root | Adapter delegates to an existing base builder. Receipt says 0/500 ms grids, explicit no-trade and separate unknown-flow handling. It is venue BBO, not national NBBO. |
| ES feature construction | `code/scc_build_fomc_es_features.py` | Feature output recorded as `features/FUTURES_FEATURES_FOMC.parquet` | Reads MBP-1 BBO and trades; preserves `ts_event`, sequence/source ordering, price, size, action, side, bid/ask and displayed sizes. It creates returns, spread/depth, update age/count, signed/unknown flow and validity flags. ES flow is a scaled price×contracts proxy without multiplier. |
| Response diagnostics | `code/scc_summarize_fomc_response.py` | Native DBN named in download receipt | Handles record ordering and BBO validity/retraction states. This is a useful input-quality diagnostic but no output was opened here. |

The actual SCC root from `results/DATA_RECEIPT.json` is `/project/econdept/qluo/bidirectional_information_20260922/fomc_information_arrival_20260922`; it records raw data as `SCC_ONLY`. The receipts establish 2023/2024 data/feature completion but do **not** establish a complete SPY basket, national NBBO, historical PCF, point-in-time index constituents, or 2015 NYSE-event coverage.

## Reuse decision

The appropriate next engineering use is a clearly labeled SPY–ES measurement prototype using the two earliest 2023 FOMC event/control pairs identified from receipt metadata (2023-02-01/2023-01-25 and 2023-03-22/2023-03-15). It can test clock alignment, BBO validity, normalized two-instrument deviation, update activity and recovery-code mechanics. It cannot identify an exogenous channel restriction, establish information shares from one-second prediction, or substitute 23 stocks for a complete S&P 500 basket.

Old earnings/FOMC empirical outputs and archived financial/result materials were not opened. In particular: prior one-second G is not an information share; the 48 earnings candidate first-public clocks remain unverified; and existing cash data are venue BBO rather than national NBBO.
