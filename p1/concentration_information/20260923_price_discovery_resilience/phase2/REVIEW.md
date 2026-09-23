# Paper 1 Phase 2 independent numerical review

Date: 2026-09-23. Scope: the final code and SCC-derived aggregates for the 2023-01-24 NYSE opening-auction failure only. I did not delegate, purchase data, copy raw rows off SCC, commit, or push.

## Decision

**`LIMITED_PASS`**.

The 503-security roster, 349 historical NYSE listings, event path endpoints, normal-band calculations, recovery implementation, first-window activity ratios, and event AUC values all reproduce from the final SCC aggregates. Job `7703146` wrote 82,511 one-second path rows and exited with the completion receipt shown in its log. The local analysis code and SCC analysis code have the same SHA-256 (`81a04f5d118adc6eeb050ebaa14b709a3720e7014f0c1c52f406a3de3aab66c7`), and the local/SCC analysis receipts also match (`ceb32c484faf6d4531b019c0dd2891fa2e9295a43b47a4b6cf0d6842273df859`).

The limitation is substantive but bounded: the three opening basket-band exceedances are not broad cross-sectional dislocations. At +4 seconds the composite drops MMM, and at +30/+31 it drops CVS, because individually valid direct-feed quotes form a crossed cross-feed BBO. Under the predeclared no-renormalization formula, dropping one constituent mechanically lowers the basket. Carrying the single affected name from the preceding valid second removes each exceedance. Therefore the reported opening `RECOVERED_30_CONSECUTIVE_VALID_SECONDS` result is numerically correct for the frozen estimator but should not be narrated as evidence that the cash/ETF/futures system broadly lost and then restored consistency.

## Independent checks

### Roster and treatment evidence: PASS with source caveat

- SCC roster: 503 rows, 503 unique PERMNOs, 503 unique tickers, 503 complete prior-close prices, weights summing to `0.9999999999999999`.
- Historical `exchcd == 1`: 349 issues.
- XNYS administrative validation divides those 349 into 308 with event opening-price-stat absence plus reference support and 41 with an event opening-price statistic requiring reconciliation; there are no historical-NYSE rows in the output's unknown category.
- This is not clean feed-level proof that all 349 failed. Databento labels `XNYS.PILLAR` on 2023-01-24 as **degraded**, while `XNAS.ITCH`, `ARCX.PILLAR`, and `GLBX.MDP3` are marked available. Absence of an XNYS record on that date must remain corroborating evidence under the SEC incident scope, not proof by absence alone.

### Event path, coverage, and one endpoint: PASS

All 7,201 post-open seconds meet the 95% basket-weight threshold. Post-open covered weight has minimum `0.9867533442`; 46 seconds are below complete coverage. Coverage is `0.9961063344` at 09:30:00, `0.9980666143` at +4 seconds, `0.9967316024` at +30/+31, and `1.0` at +60.

At +60 seconds, directly from `COMPOSITE_PATHS.csv`:

| Path | Raw midpoint/value | Normalized path |
|---|---:|---:|
| cash basket | 0.9946140637 | 0.9993242722 |
| SPY | 398.350 | 0.9984960521 |
| ESH3 | 4012.625 | 0.9985690733 |

The corresponding signed deviations are basket–SPY `+8.2822 bp`, basket–ESH3 `+7.5520 bp`, and SPY–ESH3 `-0.7302 bp`. The output and code consistently label the equity construct `THREE_FEED_COMPOSITE_BBO_NOT_NBBO`; it is not national NBBO or complete NMS coverage.

### Normal band and opening recovery: numerically PASS, interpretation limited

The same-clock 97.5th-percentile band uses ten fixed reference sessions whenever supported. At the exact open the basket pairs have `normal_n = 9` because 2023-01-18 lacks one basket observation; at +4, +30, and +31 seconds `normal_n = 10`. Across the 7,501-second collection grid, basket–SPY has ten observations at 7,338 seconds and basket–ESH3 at 7,339 seconds; SPY–ESH3 has ten at 7,499 seconds.

Independent recovery recomputation matches `RECOVERY.csv`:

- basket–SPY and basket–ESH3 first exceed their bands at +4 seconds; the only first-minute exceedances are +4, +30, and +31;
- the first 30-second all-valid in-band run starts at +32 and is confirmed at +61, so the stored recovery-start second is +32 and elapsed time from first exceedance is 28 seconds;
- SPY–ESH3 has no detectable opening loss.

The implementation matches the documented finite correction: it searches the first 60 seconds after each marker for an exceedance, then searches for 30 consecutive supported in-band seconds. The stored `recovery_second_from_open` is the **start** of the qualifying run, not the later confirmation time.

### Constituent decomposition of the isolated spikes: LIMITED

The raw BBO files were read in place on SCC only. An independent minimal DBN decode reproduced the relevant venue quotes.

- **+4 seconds:** MMM is the only missing composite constituent (weight `0.0019333857`). Its individual venue quotes are valid, but XNYS bid `116.32` exceeds the XNAS/ARCX ask `116.30`, so the cross-feed composite is crossed and MMM is dropped. Its missing basket contribution is `-18.4092 bp`. The reported basket–SPY gap is `-14.7903 bp`; carrying MMM from +3 changes it to `+3.6759 bp`, below the `12.6066 bp` normal band.
- **+30 seconds:** CVS is the only missing composite constituent (weight `0.0032683976`). XNYS bid `86.50` exceeds XNAS ask `86.49`; each venue quote is individually valid. The missing CVS contribution is `-32.6787 bp`, 21.44% of the total absolute constituent move and 125.2% of the signed `-26.0064 bp` basket–SPY gap (other names offset part of it). The top three absolute basket contributions are CVS `-32.6787 bp`, XOM `-9.7436 bp`, and WMT `+7.2539 bp`, jointly 32.59% of total absolute constituent movement. Carrying CVS from +29 changes the basket–SPY gap to `+6.5650 bp`, below the `12.7039 bp` band.
- **+31 seconds:** the same crossed CVS composite persists. The reported gap is `-26.3156 bp`; removing the one-name omission again puts the diagnostic gap inside the `13.6102 bp` band.

At +30 the 502 observed constituents are not moving in one direction: 256 are below their pre-open midpoint, 243 above, and 3 unchanged; the cross-sectional median return is `-2.48 bp`. Thus the isolated spikes are dominated by a one-name composite-validity/coverage effect, not a broad basket dislocation.

### First-window NYSE-listed activity: PASS with an endpoint-label caveat

For the saved `OPEN_0_300S` window, the event divided by the ten-session same-window median is:

| Measure | XNYS | XNAS + ARCX combined |
|---|---:|---:|
| midpoint-change seconds | 0.8714 | 0.8523 |
| trade count | 0.6301 | 0.9308 |
| trade notional | 0.2708 | 0.9512 |
| valid quote seconds | 0.9151 | 0.9960 |

For the combined alternative venues I summed XNAS and ARCX within each date before taking the ten-date median. A small labeling discrepancy remains: `OPEN_0_300S` includes integer seconds 0 through 300, hence 301 one-second buckets and trades timestamped in the 09:35:00 bucket. It is not a strict 300-bucket `[09:30:00, 09:35:00)` window, although all reported values consistently use the saved definition.

### Event AUC rank against ten normal sessions: PASS by independent recomputation

Ranks below are descending among all 11 sessions (`1` = largest AUC). The SCC `DEVIATION_AUC.csv` contains the event values; ranks were independently computed from `COMPOSITE_PATHS.csv` because the final code does not export a normal-session AUC ranking table.

| Pair | 0–300 s AUC / rank | 0–1,800 s AUC / rank | 0–7,200 s AUC / rank |
|---|---:|---:|---:|
| basket–SPY | 1,148.472 / 8th | 9,665.271 / 5th | 34,509.856 / 5th |
| basket–ESH3 | 1,097.780 / 9th | 9,095.182 / 5th | 30,035.333 / 7th |
| SPY–ESH3 | 75.488 / 8th | 687.789 / 3rd | 4,615.113 / 5th |

The event is not the largest-AUC session for any pair or horizon. Reference support is complete except that 2023-01-18 has 300 rather than 301 valid basket-pair seconds because its exact-open basket observation is absent.

## Code, data-boundary, and export checks

- The final code contains both documented finite corrections and produces disjoint activity windows.
- The direct-feed equity composite is explicitly non-NBBO throughout code and receipts.
- Credentials are read only from `DATABENTO_API_KEY` in the SCC process environment; no credential value is present in the reviewed phase-2 files or receipts.
- No DBN or parquet file exists under the local phase-2 tree. Raw DBN inputs remain under the stated SCC raw directory. Git/local results contain derived aggregates, figures, metadata, and receipts only.
- One documented field is absent: `ANALYSIS_SPEC.md` says failed-auction covered weight should accompany every basket value, but `COMPOSITE_PATHS.csv` reports only total covered weight. Given degraded XNYS condition and 41 opening-stat reconciliation cases, this omitted field could not be treated as a clean binary treatment measure anyway; the omission should be disclosed rather than silently inferred.

## Disposition

No arithmetic mismatch or evidence of credential/raw-row export was found. Release is acceptable only with the following qualifications carried into any results narrative: (1) opening recovery is estimator-specific and driven by one crossed-composite constituent at each exceedance; (2) XNYS event-day administrative data are degraded; (3) the saved first-five-minute window has 301 buckets; and (4) normal-session AUC ranks and failed-auction covered weight are not exported by the final analysis code.

Actual model/effort telemetry: `NOT_OBSERVED`.
