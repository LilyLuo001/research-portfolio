# Independent data review — 2026-09-13

**Verdict: PASS for the corrected, bounded exposure/chronology metadata census.** This is not a pass for new-clock eligibility, a selected exposure authority, earnings-session support, causal identification, dependence components, or empirical power. Those remain unresolved. The licensed-source adapter passes the reviewed column-projection design check only; its execution is **NOT_RUN**.

Reviewer: separate agent `/root/p1_census_data_reviewer`, independently reproducing the load-bearing calculations. No model/effort or usage telemetry is asserted. Read-only SCC commands used `/share/pkg.8/python3/3.12.4/install/bin/python3 -B` (pandas 2.2.2). SCC HEAD independently verified as `e4b0c81b008493cf8553f1d51ae2c40f0fc4c54d`. No SCC file was written, no scheduler job was submitted, and no commit/push/merge occurred in this review.

## Scope and reproduction

The reviewer read explicit exposure columns `cusip,wave_id,effective_date,pre_etf_ownership`, chronology columns `fund_name,effective_date,announce_date,date_precision,effective_date_approx`, identifier-crosswalk metadata, and exposure lineage. For the reconstructed CSV, reads were limited to exposure/identifier/readiness/report-date metadata. Licensed archive inspection read only migration catalog, schema descriptions, and one harvest SQL text; no raw IBES, forecast, EPS, SUE, quote, price, return, CAR, outcome or estimation source was opened. The SQL's excluded `value` column name is schema evidence, not a read of its values.

Independent calculations used sorted positive doses with cutoffs `x[ceil(n/3)-1]` and `x[ceil(2*n/3)-1]`; low is `0 < x <= q1`, high is `x > q2`. A valid wave requires distinct cutoffs and nonempty low/high tiers. Calculations were written independently of the build implementation. The final source-specific query was additionally executed on SCC with directory creation disabled and CSV writes intercepted in memory. Its three CSV byte hashes exactly match the delivered inventory, reuse and chronology summaries. The reconstructed inventory was independently regenerated in memory locally and also matched byte for byte.

| Verified quantity | Free parquet | Reconstructed CSV |
|---|---:|---:|
| Total unique stock-wave cells | 6,377 | 8,826 |
| Waves | 49 | 30 |
| Positive-dose cells | 6,377 | 8,801 |
| Positive `primary_ready` cells | Not provided | 8,801 |
| Valid old-clock tier waves | 48 | 27 |
| Low cells in valid tier waves | 2,142 | 2,943 |
| High cells in valid tier waves | 2,109 | 2,923 |

The free source has 2,241 unique CUSIPs, 1,541 appearing in multiple waves, and a maximum of 23 waves per CUSIP. Its sole invalid tier wave is W039, dated 2024-06-24, with one positive-dose cell. The reconstructed positive/readiness population has 3,440 PERMNOs, 2,380 reused across waves, and maximum reuse 16; these counts use a different security key and population.

All 49 free-source wave dates match chronology entries, representing 89 constituent event rows. Every selected constituent has a nonblank, parseable ten-character announcement date. Nine selected effective dates have multiple constituent announcement dates. `date_precision` and `effective_date_approx` are blank in all 89 selected rows. These checks establish date presence only: the join is by effective date and does not establish signed package membership or the earliest relevant public announcement/anticipation clock.

## Authority and limitations

The parquet lineage output hash and its current `events_merged.csv` input hash agree. The lineage names `t2_wrds/waves.csv`, but this review does not certify that additional input's content. The four-column crosswalk contains 2,247 rows and 2,241 unique CUSIPs, including every selected free-source CUSIP. It is ancillary identifier metadata, not the reconstructed exposure CSV.

The actual reconstructed exposure file is evidence E007, with a separate September construction lineage. Its 8,801 ready/positive cells cannot be replaced by the 6,377-cell July free parquet merely because the latter is present in this SCC checkout. The versions share 20 effective dates, with 29 free-only and 10 reconstructed-only dates. This calendar comparison is reproducible; cell-level equivalence is unverified without a validated point-in-time key bridge and provenance reconciliation. No pooling or final authority selection is approved.

Announcement time/timezone and usable timing uncertainty are not supplied by these inspected chronology/exposure views. Missing time does not categorically prevent conservative date-interval ordering. However, the free exposure view lacks holdings report/publication/denominator dates for such a test, and the reconstructed report dates have not been joined to a versioned announcement/publication clock. Strict pre-announcement eligibility is **UNKNOWN**, not a measured zero. Old-clock tiers are provisional diagnostics, not approved sample membership.

CUSIP/PERMNO reuse is not a connected-component count or effective sample size. Raw adviser/Dimensional labels in the reconstructed CSV do not establish signed economic sponsors. Earnings-event identity, timezone/session rules, horizon/common-SPY masks, clean controls, response-leg dates and sponsor components are not measured by this census.

The new archive check correctly limits prior absence claims: the archive catalog lists annual IBES partitions for 2019–2026, an identifier file and an exchange-calendar file. The eight adapter projection columns exist in the archived IBES schema and 2025 SQL; the `value` field is excluded. The schema provides no unique economic-event/revision rule or timezone convention; the calendar schema provides no open/close or early-close instants. Thus the unexecuted adapter would deliver candidate source records, not unique economic events or session counts. Missing partitions, unresolved mappings, and its fixed date window must remain explicit in any eventual execution receipt. Its authorization-reference argument is not itself authorization.

The final `SOURCE_SPECIFIC_QUERY.py` enforces pinned parquet and chronology hashes before parsing or creating outputs. The reviewer independently verified the SCC inputs pass and the local advanced snapshot's different chronology hash `e5a441368fcadb53064c226d4d90a858f5024fce14a90d913cf8dfb127a67a4e` is rejected, with zero output-directory, CSV-parser and parquet-parser calls. The general `code/inventory_sources.py` and unexecuted custodian adapter do not enforce this exposure-source manifest. This PASS is tied to the source/code/output hashes below; a future source version requires rechecking the manifest and rerunning verification. Aggregate SUPPORT/DEPENDENCE tables include manually stated unavailable stages and are not all byte-generated by the source query. Their measured entries were checked separately; unavailable entries cannot be read as zero support.

## Corrections required during review and resolved

The initial source-selection narrative confused the crosswalk with the actual reconstructed exposure CSV; corrected source selection keeps the two exposure versions separate. Initial pandas linear interpolation reproduced 2,132 low/2,141 high free-source cells but did not implement the inverse empirical CDF; corrected counts are 2,142/2,109. The reconstructed inventory initially permitted nonpositive cells in low-tier counts and did not require a nonempty upper tier; both conditions are corrected. Strict eligibility changed from a hardcoded zero to unknown. Date-only evidence now permits conservative ordering in principle. The final free chronology summary is scoped to the selected 89 constituents/49 wave dates and byte-matches the reviewed query.

## Exact source and reviewed artifact hashes

SHA-256; SCC exposure paths are relative to `/usr3/graduate/qluo/dax-codex`. Reconstructed paths are relative to `/Users/lilyluo/research-portfolio-p1-advanced-readonly`. Archive paths are relative to `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902`. Build paths are relative to this review's directory.

| Source | SHA-256 |
|---|---|
| SCC `p1/conv_exposure_free.parquet` | `350c3c7aed6d1bf047a8970f4d5940f37f1ec89e012876cb0f081668a5d2b4e7` |
| SCC `p1/conv_exposure_free.parquet.lineage.json` | `ff26b812b5849825d9df0aa6b98815066564739596b2413c09b28656f89d116a` |
| SCC `p1/events_merged.csv` | `758b2aeb5655ab48f50f53717e2c74d0b35f4a8fcae8df9f1f30b61b2023a821` |
| SCC `p1/t2_free/conv_exposure_free_crosswalk.csv` | `0bf63d37896fca60822d9ad773451c3b13935c5438e1a68c01d17ee9da353b3e` |
| Reconstructed `p1/exposure/exposure_stock_wave_all.csv` | `905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320` |
| Reconstructed `p1/exposure/exposure_construction_lineage.json` | `c0c0f817068609ff4c20ef4eb21958932d35a785390733d9b5c7993475aaff4a` |
| Archive `_migration_meta/FINAL_SCC_MANIFEST.tsv` | `ce2f23683d69d89fae705363f4dadc0e551f639684c2980210c960753ff3e3bb` |
| Archive `p1_refraction_wrds_shared/meta/schema__ibes__actu_epsus.csv` | `699243e0905d1916452bfb05ee3937e9684f3830c1a2d546f2b2cefe38a43934` |
| Archive `p1_refraction_wrds_shared/meta/schema__crsp__metaexchangecalendar.csv` | `729adb0a99719eb4ced7637643e66dc904687d67f9226da2c0e93d94460930d6` |
| Archive `p1_refraction_wrds_shared/meta/ibes_actuals_eps_2025.sql.txt` | `5dbdc44a2ef1771bf1786a2952c3734de1f500f60413b991ce756e51b42a288d` |

| Reviewed build artifact | SHA-256 |
|---|---|
| `SOURCE_SPECIFIC_QUERY.py` | `da6e0e6a2c957a205939bee01406d64c85883f071f685c00952b91ca5b471bfa` |
| `code/inventory_sources.py` | `27019f35e824ccbca08ede701766cd759dc20fa4f9e79398fc7a9738b6882499` |
| `code/custodian_projection.py` | `1fb0f8df878df4e61f2fa83214690b997246ca274257423e8bc4c1d02c70b59e` |
| `free_source_inventory.csv` | `fbb0be83524481ba6a66ee6da1f4c4ba92d608a7559ec35ac0c0ae0f521e33b2` |
| `free_reuse_summary.csv` | `a454f9cc73021c1ec5fa61f5b9ac9b69cf85062abd34590dcf3c05989417f11a` |
| `free_chronology_summary.csv` | `2af470a2e93b7ecc69312a9ceba3b47ac17216c65c113048d1073ff2a8b90fd2` |
| `advanced_source_inventory.csv` | `0bd24dfa4d10e7b3725ae6c295a54d50fa229df19c8d19f9df0bf468dba66280` |
| `source_comparison_by_effective_date.csv` | `98ee57a6e34e36cad903282025fd865cde77a72fecdb43521545917b498ec7f7` |
| `source_comparison_summary.csv` | `145ca8f12742f216929f5848dae0f0ae8e5c4f44c4041d82fb76bb2c4abd5576` |
| `chronology_uncertainty.csv` | `10d83f7338ba7baaf1e67acdffc84057e537ff03c5fe200961687047b7fc8821` |
| `SUPPORT_CENSUS.csv` | `28db0aee10426939028ea6e3b6834593751a5bf080ce3cff59bb94b744e276c8` |
| `DEPENDENCE_CENSUS.csv` | `63921952b46547b1a67c4052a0b834ab1c42167c57bbce95ecd3f606ca9a244f` |
| `SOURCE_SELECTION.md` | `5ae65cd817edd24e37941b29a1b48c37aac7e2e8f219e59d61bda6235f035fc1` |
| `ARCHIVE_CATALOG_CHECK.md` | `5a1f44907552bbbb28feafa4fe3bd08894115131d64e8ef12e97bdc8ea009d89` |
| `PROTECTED_SOURCE_ADAPTER_REQUEST.md` | `16f677e5d06285d75ced0e8ad28948536d06dc1a1e019b5c4a131fb6f460f32f` |

RUN_MANIFEST/RECEIPT status fields and the coordinator's final decision prose may be updated after this review; no certificate of their future hashes is implied. Any change to the reviewed code, measured outputs or source-selection/handoff content above requires an appended recheck.
