# P1 missing-data acquisition: extended checkpoint

Date: 2026-09-14  
Scope: acquire/build inputs requested by the relevant P1 zip plans. No identification, treatment-effect, empirical-power, or final-design decision. No GPT-6 referee in this phase.

## Acquired or built

- Five-wave strict pre-announcement holdings: 12 equity predecessor series, 10,010 positions, and 9,458 common-equity candidates.
- CRSP identity/denominator/liquidity inputs: 9,342 exactly mapped positions, 2,779 unique PERMNOs, and 4,191 positive stock-wave exposure candidates.
- Outcomes-blind tail support pool: 2,088 stock-wave candidates have complete 8 PRE + 4 POST earnings-metadata support under the recorded acquisition cutoffs.
- Acquisition-only supported roster: 40 stock-wave units, eight per wave, with 40 unique PERMNOs. This is not the final analysis roster because the original plan does not fully specify the authoritative liquidity metric, ordering, tie handling, or reserve rule.
- Competing-conversion screen: under the proposed (not final) `announcement cutoff +/- 24 months` rule, the 2,088-member full-support pool contains clean high/low counts of W002 `116/347`, W013 `0/0`, W016 `12/14`, W021 `0/0`, and W025 `16/3`. Thus a five-wave 40-unit clean roster is mechanically impossible under that proposal; the maximum balanced acquisition roster is 23 units across W002, W016, and W025. W013 and W021 have no clean candidate, and W025-low has only three.
- To avoid spending only on future exclusions, the Databento acquisition population is the union of the original five-wave measurement roster and the maximum proposed-clean roster: 62 unique stock-wave units. The union deliberately keeps overlap/stress observations but adds the clean candidates needed for a later adjudication.
- A full-pool forecast audit then found 895 stock-wave candidates whose twelve selected events each have at least two analysts. Intersecting this with proposed overlap-clean status leaves W002 high/low `10/165`, W016 `2/1`, W025 `2/2`, and W013/W021 `0/0`. The maximum fully supported clean acquisition subset is therefore 15 units, not 40. The final acquisition union adds these scarce candidates and contains 71 unique stock-wave units.
- Exact companion-event inputs: 480 unique stock-period associations (320 PRE, 160 POST), 480 date-valid historical raw symbols, 480 licensed actual-source rows and 6,112 forecast rows in the 90-day envelopes. Actual and forecast values remain SCC-only.
- Union companion-event inputs: 744 unique stock-period associations (496 PRE, 248 POST), 744 date-valid symbols, 744 licensed actual rows, and 7,315 forecast rows on SCC. Of these, 553 have at least two analysts.
- Final acquisition-union inputs: 852 associations (568 PRE, 284 POST), 852 date-valid symbols, 852 licensed actual rows, and 8,193 forecast rows on SCC; 659/852 have at least two analysts. The separately selected 15-unit clean/analyst subset has all 180 events at the minimum-two-analyst threshold by construction.
- Forecast coverage: 383/480 associations have at least two distinct analysts in the 90-day envelope. This is coverage metadata, not a computed SUE.
- Trading calendar and corporate-action inputs: all 480 announcement dates are observed SPY/CRSP sessions; six association windows have a distribution flag; zero have a CRSP price-factor or share-factor change in the protected endpoint window.
- Compustat RDQ cross-check: 468/480 unique RDQ matches, 12 missing, zero ambiguous; 456/480 RDQ dates equal the IBES announcement date.
- Databento union manifest: 744 events × stock/SPY × four date-wide legs was reduced from 5,952 logical mappings to 4,171 atomic symbol requests and 1,329 grouped XNAS jobs. Broad slices avoid assuming an unverified IBES `ANNTIMS` timezone. The three alternative single-venue bundles comprise 3,987 grouped jobs and are costed separately.
- The final 852-event manifest contains 6,816 logical mappings, 4,648 atomic XNAS symbol requests, and 1,387 grouped XNAS jobs. Three alternative single-venue bundles contain 4,161 grouped jobs and are priced independently.
- Separate alternatives were compiled for ARCX, BATS and XNYS. They remain separate single-venue bundles and are not labeled an NBBO or automatically pooled.

## SCC-only licensed outputs

- `/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/supported_earnings_inputs/licensed_actuals_selected.parquet`
- `/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/supported_earnings_inputs/licensed_forecasts_90d_selected.parquet`
- `/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/event_calendar_actions/licensed_distribution_rows_selected_permnos.parquet`
- `/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/event_calendar_actions/daily_factor_rows_selected_permnos.parquet`

## Databento execution status

The exact grouped manifests and a guarded quote/download runner are ready. The runner:

- reads the key only from `DATABENTO_API_KEY`;
- performs exact cost and record-count calls before a charged endpoint;
- enforces the owner-reported USD 123 credit-only ceiling and zero cash spending;
- stages one native DBN file at a time locally, transfers it to SCC, verifies the remote SHA-256, and removes the local staging copy only after a match;
- keeps POST files in a separate `sealed_post` directory.

At this checkpoint the current Codex process does not contain `DATABENTO_API_KEY`, so no new Databento API call or purchase has occurred. A hidden terminal prompt was opened for owner entry; after entry, the prepared command quotes and downloads the selected complete bundles automatically.

## Scientific boundaries retained

- `PILOT_STOCKS_40_SUPPORTED.csv` is an acquisition roster, not a signed final population.
- IBES clock strings were preserved but their timezone was not inferred.
- No quote outcome, price response, return, CAR, treatment effect, or empirical power result was inspected.
- The index-rebalancing and corrupted stock–ETF/IRR fallback materials in historical zip bundles were not revived.
- No git commit, push, merge, authentication change, or data purchase outside the guarded Databento path was made.

## Next phase after acquisition

Only after the Databento delivery and structural coverage receipts are complete should the requested GPT-6 referee assess whether the measurement support is sufficient for an identification/power adjudication. This checkpoint does not make that decision.
