# Quote acquisition metadata inventory (P0, read-only)

Created 2026-09-20 from archived receipts only. No API call, purchase, DBN decode, quote/return value, credential, or licensed row-level export was performed.

## Authoritative sources

- `p1/execution_archive/20260915/artifacts/pilot_workspace/missing_data_round_20260914/databento_final_acquisition/manifest_receipt.json` — **planned manifest only**: 852 event inputs, 4,648 deduplicated core physical requests, 2019-01-29 through 2024-12-11; explicitly 0 API calls/downloads.
- `p1/execution_archive/20260915/artifacts/pilot_workspace/gate1_20260915/header_audit_receipt.json` and `DECISION.md` — **latest authority**: 5,544/5,544 selected jobs present, size matched, and header contract matched; 5,548 planned jobs minus four named quote/query failures. This supersedes the earlier transfer-stage 3,787/1,154/600 checkpoint for structural status; explicit gaps remain.
- `p1/execution_archive/20260915/artifacts/pilot_workspace/delivery/QUOTE_RECEIPT.json` — metadata/catalog and request quote receipt, not a download receipt. It records `XNAS.ITCH` and `ARCX.PILLAR` with `bbo-1s`/`bbo-1m` available from 2018-05-01; its bundle flags are quote/catalog status, not physical-file verification.
- `.../delivery/DOWNLOAD_MANIFEST.csv` is the documented physical-file manifest for the separate delivery workflow; archived code says blocked/no attempt when credentials or owner approval are absent. Do not infer files from catalog or quote status.

## Safe dataset/schema/interval inventory

| dataset | schema | documented UTC coverage/request interval | status | physical-file status |
|---|---|---|---|---|
| XNAS.ITCH | bbo-1s | catalog range 2018-05-01T00:00:00Z to 2026-09-12T00:00:00Z; planned manifest event windows 2019-01-29–2024-12-11 | catalog AVAILABLE; selected core bundle | latest header audit: selected jobs structurally accounted for; body integrity/live quote coverage NOT_ASSESSED |
| ARCX.PILLAR | bbo-1s | catalog range 2018-05-01T00:00:00Z to 2026-09-14T04:00:00Z; alternative planned windows in same manifest date span | catalog AVAILABLE; selected alternative bundle | aggregate download receipt only; no event/symbol-level completeness exported |
| BATS.PITCH | bbo-1s | catalog range 2018-05-01T00:00:00Z to 2026-09-14T04:00:00Z; alternative planned windows in same manifest date span | catalog AVAILABLE; selected alternative bundle | aggregate download receipt only; no event/symbol-level completeness exported |
| XNYS.PILLAR | bbo-1s | catalog range 2018-05-01T00:00:00Z to 2026-09-14T04:00:00Z; alternative planned windows in same manifest date span | selected alternative bundle | aggregate download receipt only; no event/symbol-level completeness exported |
| XNAS.ITCH / ARCX.PILLAR | bbo-1m | catalog ranges as above; no new physical request established by this inventory | catalog AVAILABLE | NOT_OBSERVED as a downloaded physical schema in the final acquisition receipt |

The proposed research request remains BBO-1s, approximately `[-15,+75]` minutes around a frozen announcement clock, split by session when needed. Latest Gate 1 metadata reports 18,387 date-valid mappings, 191 NOT_FOUND and 14 UNKNOWN among 18,592 job-symbol rows; 6,766/6,816 core XNAS logical legs supported; 839/852 associations with all eight legs mapped. These are structural metadata counts, not live-quote coverage. The 2023 roster/event overlap is **NOT_OBSERVED** here and must come from the new SCC roster worker.

## Interpretation

Downloaded/verified means only the aggregate states in `scc_direct_receipt.json`; it does not certify all symbols, event windows, or coverage. “Catalog AVAILABLE”, “QUOTED”, and “selected bundle” are planning/metadata states, not proof of a local file. Luna/low telemetry: **NOT_OBSERVED**.

## SCC execution (latest final manifest)

Executed `inventory_metadata.py` on `/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native/control/download_manifest.csv` (5,544 rows; SHA-256 of local compact output `scc_inventory_summary.json`: `bbd74eff77a38009fe1c0dc97fce2fa8006239619c011f114dc3e80a44eb59b1`). Actual columns were: `job_id,bundle,dataset,schema,symbols,start,end,analysis_access,quoted_cost_usd,reserved_cumulative_usd,path,local_staging_path,bytes,sha256,error_type,completion_status,warning_count,warning_types`. All rows are `bbo-1s`; years span 2019–2024.

The compact output is [scc_inventory_summary.json](scc_inventory_summary.json). It preserves source-specific statuses (including verified-on-SCC, transferred-unverified, on-SCC-unverified, and authorized-retry) and does not inspect DBN bodies.
