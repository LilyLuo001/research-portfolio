# Independent acquisition review — PASS

Review date: 2026-09-14 (Asia/Shanghai)

Requested reviewer route: `gpt-5.6-sol/high`. Actual routing/effort telemetry:
`NOT_OBSERVED`.

## Scope and conclusion

PASS. The fixed P1 acquisition is complete and internally consistent after the
finite corrections listed below. I independently checked immutable inputs,
pinned membership evidence, exact Decimal quote arithmetic, frozen selection,
all selected native files, access separation, dataset conditions, event
coverage, PRE-only schema/venue aggregates, and delivery leakage controls.

I did not access credentials, call Databento, open SCC, inspect POST_FOCAL quote
values, perform treatment/effect/power analysis, or push/commit. The independent
DBN reproduction opened only the 172 PRE-only files and the PRE-authorized
subwindows of the eight mixed files. It did not open the 194 pure POST-only
files and did not emit quote values.

One financial limitation remains disclosed rather than silently resolved:
actual billed credits are pending the vendor billing receipt. This review
verifies the exact quoted/reserved gross usage and the completed file delivery;
it does not represent the pending vendor billing figure as observed.

## 1. Immutable inputs and pinned membership evidence — PASS

All 18 entries in `manifest_hashes.json` were recomputed from bytes and matched:

| Input | SHA-256 |
|---|---|
| `CHECKS_RUN.md` | `7e32d380baa989c56406b3501300c1d527f1ed150822b78b6654e740ad741257` |
| `CODEX_EXECUTE_ORDER.md` | `ee97b5ade67ce8f72b365d4f7a5237660b8042050408835b701d11e035cb6ec6` |
| `DATE_SOURCES.md` | `2bfd2588f3a8e4f55ca20b12f305d81f2cc95f0ac16b4bf0598e09bbc87e011e` |
| `PILOT_DATA_ORDER.md` | `ff6563784794cbca6e1e8d6430eccdde7d4b14872023115383d159f4708eadea` |
| `START_HERE.md` | `d5bd8a123517a439362494ac4abebfad6b370f9a642cf47122c59937779f36a3` |
| `budget_gate.py` | `85882413fec01ec7064bae90ab7644f30c2946f4604e5afabcc774d5a18ccaf4` |
| `build_order.py` | `07431ac00ccd14d32cc2358d3b5af0a3f2d1d1d9a2bceaa2beb6f12548969939` |
| `conversion_cohorts.csv` | `119efd4452f6554aace35bfc85726ec63973b2995a3c41c50570309914fe2d91` |
| `core16_budget_reduction_requests.csv` | `b9d6edfe5aa82bdc04d59f20d37eb8cce1783511bed16e29adacc893413edb01` |
| `core16_event_request_map.csv` | `0ab0c9395e30964284a1d7ac4a0aee6d7e38cc85cef5df8ecd6d9c8999410f41` |
| `core32_event_request_map.csv` | `c96b77f28e626d3571fd5e67e95879d146c56c3011efac290894c0cd77fb9902` |
| `core32_requests.csv` | `68537611e18e113599aa596e9f0a0dda5e732df33d3e9e9d7d8ab202a3674413` |
| `earnings_events.csv` | `f1bda25f0cf4120e98251ed66afaa6e8a420844daef7b5385c59de4f83075bd6` |
| `extra_etf_requests.csv` | `a7a40a3c460686db429f5994881cde82d8cc67ed1be19a167144a254b0f99191` |
| `extra_event_request_map.csv` | `0181c24e70316572401738421687e73dee7a180f8777b17bf43140c3ea6535f9` |
| `order_summary.json` | `82014249a05c56c439517d2113dac6a82a6fb3c88ca99bbf6d5cf07e8ee69359` |
| `securities.csv` | `2b56bc39fb056113cef4c5c2fd7cb78664801e6999636b98b021c7779c3ffe8c` |
| `validation_requests.csv` | `68e0d9cf0406009c3404850a9a52e57b0143734015b7ab9a971c76dc6a0f3072` |

Read-only `git show` at repository commit
`cb36417304b282cda5e38ede13d1af872ad9f346` independently verified the
crosswalk evidence. Exact ticker/PERMNO/wave/as-of matches, all with
`mapping_status=exact_matched`, were found as follows:

| Ticker | PERMNO | Wave | As-of | Matching crosswalk rows |
|---|---:|---|---|---:|
| JJSF | 10026 | W002 | 2021-04-30 | 4 |
| PLXS | 10032 | W002 | 2021-04-30 | 4 |
| MSFT | 10107 | W002 | 2021-04-30 | 2 |
| ORCL | 10104 | W002 | 2021-04-30 | 2 |
| SKYW | 10421 | W016 | 2022-12-30 | 1 |
| AXL | 86547 | W016 | 2022-12-30 | 1 |
| AROC | 92245 | W016 | 2022-12-30 | 1 |
| BHE | 76224 | W016 | 2022-12-30 | 1 |

The committed bytes of `p1/exposure/exposure_stock_wave_all.csv` at that
commit independently hashed to
`905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320`,
matching the E007 hash recorded for all eight securities.

## 2. Quote arithmetic and frozen budget selection — PASS

I summed every constituent quote with Python `Decimal`, without floating-point
conversion:

| Bundle | Requests | Recomputed USD | Receipt match |
|---|---:|---:|---|
| core16 | 115 | 0.409266650676 | yes |
| core32 | 220 | 0.769090354444 | yes |
| validation_mbp1 | 8 | 0.160355865954 | yes |
| validation_arcx | 8 | 0.008400678635 | yes |
| extra_etfs | 138 | 0.640460848816 | yes |

The frozen choice is exactly `core32 + validation_mbp1 + validation_arcx +
extra_etfs`. Its 374 unique canonical requests sum to
`1.578307747849` USD, exactly matching `SELECTION_RECEIPT.json`. The choice is
within the 100 USD planning cap, the 125 USD hard ceiling, and the owner's
current stated 125-credit balance. The resulting uncommitted amount relative
to the hard ceiling is `123.421692252151` USD.

The quote receipt contains 375 canonical alternatives because it also retains
the fixed core16 fallback; the selected union contains 374. The quote-receipt
hash, sorted selected-request hash, and selection-to-cost receipt hash links
all match. Final selection status is
`FROZEN_QUOTED_BUNDLE_SELECTED_AND_PURCHASED_COMPLETE`.

## 3. Download manifest and access handling — PASS

`DOWNLOAD_MANIFEST.csv` contains 374 rows, 374 unique canonical IDs, and exactly
the same ID set as the frozen selection. All 374 rows have
`completion_status=DOWNLOADED_NATIVE_DBN_UNINSPECTED`. For every row I verified:

- the path exists under the delivery directory;
- the file is nonempty;
- actual bytes equal the manifest byte field; and
- independently recomputed SHA-256 equals the manifest SHA-256.

There were zero missing, zero byte-mismatched, and zero hash-mismatched files.
Independent classification from the event maps and event access flags gave:

| Access class | Files | Handling |
|---|---:|---|
| PRE-only | 172 | `native_pre_focal`; authorized PRE QA |
| Mixed | 8 | `sealed_post_focal`; only mapped PRE subwindows used |
| POST-only | 194 | `sealed_post_focal`; existence/bytes/hash only |

The eight mixed files are four SPY and four IWM unioned intervals on
2021-10-26 through 2021-10-29. They are shared by temporally overlapping PRE
and POST event maps. This is why physical-file classification differs from the
row-level source access label. The final manifest reports 172
`PRE_STRUCTURAL_QA`, eight
`MIXED_FILE_PRE_SUBWINDOW_QA_POST_VALUES_UNINSPECTED`, and 194
`POST_SEALED_STRUCTURAL_ONLY`.

## 4. POST sealing and leakage review — PASS

Code-path review found one DBN quote-field access site: `pre_metrics` in
`finalize_post_download.py`. Pure POST files return a structural-only status
before that function is called. For mixed files, the iterator obtains a receive
clock, tests it against the union of exact PRE-authorized `[start,end)` windows,
and dereferences bid/ask price and size fields only after the clock passes that
test. In-memory states feed only aggregate counts/equality results; no quote
state is serialized.

The independent reproduction followed the same access boundary: 180 permitted
files/subwindows were read, 194 pure POST-only files were not opened, and no
quote values were printed or written. Delivery CSV/JSON/Markdown surfaces had
zero occurrences of bid/ask quote-field names. All 256
`POST_SEALED_UNINSPECTED` coverage rows now have blank observed clocks and
`record_count=NOT_INSPECTED`; all 194 pure POST manifest rows have no QA clocks
and `qa_records`/`qa_instrument_ids=NOT_INSPECTED`. `COST_RECEIPT.json` records
`post_focal_values_inspected=false`.

A credential regex scan over all delivery/source text, Python, CSV, JSON, and
Markdown files checked Databento-key, generic literal key/token/secret/password,
JWT, AWS access-key, and private-key markers. It found zero credential
candidates and printed no candidate values.

## 5. Dataset conditions — PASS

The selected requests independently imply 92 XNAS.ITCH dates and four
ARCX.PILLAR dates. These 96 dataset/date pairs exactly equal the requested-date
and returned-condition sets in `DATASET_CONDITIONS.json`: 95 are `available`;
the sole exception is XNAS.ITCH on 2021-10-26, `degraded`. The degraded pair is
preserved in `DATASET_CONDITION_OVERRIDES.json` as
`DEGRADED_VENDOR_METADATA_QUALITY_EXCEPTION`, not recoded as zero or ordinary
coverage. Final outputs identify six affected files and 11 affected event legs.

## 6. Event coverage and strict PRE-event rule — PASS

I rebuilt coverage from the two event maps, immutable request manifests, event
access flags, exact New York-to-UTC bounds, and permitted DBN receive clocks.
The 448 independently generated event-leg statuses exactly matched
`PILOT_COVERAGE.csv`:

| Map | Rows |
|---|---:|
| Core32 stock/SPY event legs | 256 |
| Optional ETF event legs | 192 |
| Total | 448 |

Status counts are 192 `OBSERVED_PRE_COVERAGE` and 256
`POST_SEALED_UNINSPECTED`. Applying the strict rule—PRE access, all eight named
core stock/SPY legs present, and every one observed—returns exactly these 16
events:

`W002_JJSF_20190729`; `W002_JJSF_20200127`;
`W002_MSFT_20191023`; `W002_MSFT_20200129`;
`W002_ORCL_20190911`; `W002_ORCL_20191212`;
`W002_PLXS_20191023`; `W002_PLXS_20200122`;
`W016_AROC_20211101`; `W016_AROC_20220509`;
`W016_AXL_20211105`; `W016_AXL_20220211`;
`W016_BHE_20211027`; `W016_BHE_20220426`;
`W016_SKYW_20211028`; `W016_SKYW_20220428`.

This is only an acquisition/coverage rule; no treatment or effect calculation
was run.

## 7. PRE schema and venue aggregates — PASS

For the eight XNAS comparisons I treated each BBO `ts_recv` as the interval-end
clock and selected the last MBP-1 state at or before that endpoint with
`bisect_right`. MBP candidates were restricted to the validation slice itself,
so no state before slice start was carried in. The independent aggregates
exactly matched `SCHEMA_OVERLAP_CHECK.csv`:

| Request | Symbol | BBO endpoints | MBP compared | Matching states | No in-slice MBP state |
|---|---|---:|---:|---:|---:|
| V_001 | PLXS | 495 | 495 | 495 | 0 |
| V_002 | SPY | 3334 | 3333 | 3333 | 1 |
| V_005 | MSFT | 4104 | 4103 | 4103 | 1 |
| V_006 | SPY | 3016 | 3015 | 3015 | 1 |
| V_009 | AXL | 715 | 715 | 715 | 0 |
| V_010 | SPY | 9914 | 9913 | 9913 | 1 |
| V_013 | BHE | 414 | 414 | 414 | 0 |
| V_014 | SPY | 5587 | 5586 | 5586 | 1 |

The eight ARCX rows are explicitly venue-sensitivity coverage counts, not quote
equality or quality claims, and also reproduced exactly:

| Request | Symbol | ARCX endpoints | XNAS endpoints |
|---|---|---:|---:|
| V_003 | PLXS | 455 | 495 |
| V_004 | SPY | 3327 | 3334 |
| V_007 | MSFT | 3940 | 4104 |
| V_008 | SPY | 3117 | 3016 |
| V_011 | AXL | 553 | 715 |
| V_012 | SPY | 9917 | 9914 |
| V_015 | BHE | 694 | 414 |
| V_016 | SPY | 6185 | 5587 |

No quote values were emitted during either reproduction.

## 8. Finite corrections and contradiction check — PASS

The initial review found stale/contradictory delivery state. The coordinator
made finite corrections before this PASS was issued:

- `SELECTION_RECEIPT.json` was changed from “selected not purchased” to the
  completed-purchase status, with current-session approval provenance,
  `owner_purchase_permission_required=false`, and
  `vendor_charge_enforced=true`.
- `ACQUISITION_LOG.md` now correctly says 489 source-manifest rows canonicalize
  to 375 distinct physical requests; it no longer calls all 489 rows distinct.
- `COST_RECEIPT.json` now says
  `PURCHASE_COMPLETE_FILES_VERIFIED_BILLING_NOT_RECONCILED` rather than implying
  only offline finalization.
- The finalizer now blanks observed clocks for every POST-labeled coverage row;
  the regenerated output has zero POST rows with an observed clock.

I reran all affected receipt links, file integrity checks, condition counts,
coverage reconstruction, schema/venue aggregates, and leakage scans after
these corrections. No stale contradiction remains in the reviewed final
outputs. The intentionally pre-purchase `budget_gate.py` helper still returns a
“selected not purchased” provisional state before an authorized download; that
is correct for the helper and is not the final receipt state.

## 9. Final delivery hashes after corrections

| Artifact | SHA-256 |
|---|---|
| `QUOTE_RECEIPT.json` | `d66f07394fddf62cbe3ca61afa3b91efae69ec3610ed0c8b22ddc6b664de09bb` |
| `BUDGET_GATE_INPUT.json` | `ee07420d92cda54d4b8e67bc8efae345e2337f6130a7071fd6db1992e8293a1d` |
| `SELECTION_RECEIPT.json` | `6177957a6c15aa01a3d90f656aba8d09c7d3ed263c9fb95bfa91adf146c082a0` |
| `DOWNLOAD_MANIFEST.csv` | `acabe43de0a9671f14e89222b85947cdf56299dc63d74756bfb98dc0c5097574` |
| `SELECTED_ORDER.csv` | `ff332469a3ba493b55e383250016f3d71b77bf0ae983020f29b5713ab7597743` |
| `DATASET_CONDITIONS.json` | `679a490c75e8b25bfa60f9ec994689edc592df49d5caf09bfa32c40b506f23db` |
| `DATASET_CONDITION_OVERRIDES.json` | `15ddd9e542a1fc0f86d06f748fbfa5d3b5edb99b094cbb2e8d46b2c7e55764be` |
| `PILOT_COVERAGE.csv` | `df46f671bbbe1a00f0ceae4580bbec816dcb3e5a26e93f0e4b7bcaf451223d6a` |
| `SCHEMA_OVERLAP_CHECK.csv` | `2b99ef84e7188330cf1f180657551ba9dbaa736a7cd945832e8d6599e5991561` |
| `COST_RECEIPT.json` | `9a7ed34cf887e6e23793985681e227ba82ff088249f4e0b991811a28fc66ade0` |
| `PILOT_DELIVERY.md` | `9eb3ba1f9eb365de3584981d84981e9f5d143fca20945869d58404a4175c9817` |
| `ACQUISITION_LOG.md` | `1b50ca6bb0f89919ec89c2370080a53a2cc27e3688c61863950f444b176ad6ea` |
| `run_fixed_order.py` | `8770be1104c6764b6b7a8416e1216fca92c30fb7b95700ffac7761c102c1783b` |
| `finalize_post_download.py` | `6674b1d7873155917ab97cdcccef13b5eba385437f723338a8d7b3a45b07289f` |
| `fetch_dataset_conditions.py` | `3b3218a808fdf3697fbe59116dd2f6bde07a7383addd9ee811c038526a10e4fa` |

These hashes were taken only after the finite corrections and final rerun.
