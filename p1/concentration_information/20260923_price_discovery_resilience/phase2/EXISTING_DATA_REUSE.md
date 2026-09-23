# Existing-data reuse audit

Date: 2026-09-23. Scope is metadata, receipts, manifests, and code only. No raw or feature rows were copied from SCC. Requested routing was `gpt-5.6-terra / medium`; actual model telemetry is `NOT_OBSERVED`.

## Verified from local SCC receipts

| Existing object | Receipt-backed SCC location | Actual event-date coverage | Instruments / venue | Schema / usable fields | Reuse decision |
|---|---|---|---|---|---|
| Two-venue equity native data | `/scratch/qluo/bidirectional_information_20260922/raw/XNAS_ITCH_2023-01-24.dbn.zst`; `/scratch/qluo/bidirectional_information_20260922/raw/ARCX_PILLAR_2023-01-24.dbn.zst` | `2023-01-24T14:59:00Z`–`15:31:00Z` (about 09:59–10:31 ET) | SPY plus 23 stocks; XNAS.ITCH and ARCX.PILLAR only | `mbp-1`; quote/trade top-of-book construction and ordered event timestamps available through the existing builders | Reuse only as a post-opening, two-venue engineering/check window. It cannot identify the 09:30 opening-auction failure, create an NBBO, measure XNYS, or construct the S&P 500 basket. |
| E-mini futures native data | `/scratch/qluo/bidirectional_information_20260922/futures_control/raw/GLBX_MDP3_2023-01-24_ESV0_MBP1.dbn.zst` | `2023-01-24T14:59:00Z`–`15:31:00Z` | GLBX.MDP3; requested `ES.v.0`, resolved actual contract `ESH3`, instrument id `206299` | `mbp-1`; BBO/trades, event ordering, update/depth/flow fields through existing builder | Reuse for the same post-opening engineering/check window after entitlement and file accessibility are revalidated. It does not cover the auction or provide cash-basket/NBBO information. |
| Feature-pipeline implementation | `p1/concentration_information/20260922_directional_evidence/code/` and earlier FOMC builders | 24 sampled 2023 dates, 10:00–10:30 ET design | SPY, 23 stocks, XNAS/ARCX; futures adapter exists separately | Event clocks, BBO/trades, midpoint/spread/depth, update counts/age, signed and unknown flow, explicit no-trade state | Reuse code patterns only after adapting to consolidated cash/status inputs; do not reuse its results as the 2023-01-24 event result. |

The preceding locations and date/time bounds are recorded in `20260922_bidirectional_information/results/DOWNLOAD_RECEIPT.json`, `20260922_futures_control/results/DOWNLOAD_RECEIPT.json`, `20260922_futures_control/results/CONTRACT_MAP.csv`, and `20260922_directional_evidence/EXECUTION_RECEIPT.json`. The local receipts establish files were previously placed on SCC; they do not themselves establish current read permission, continued file retention, or entitlement for this new analysis.

## Live access audit

The first noninteractive check returned `Permission denied` because no ControlMaster existed. The user-authorized interactive login was then restored without storing a credential; `ssh -O check` reported a live master. All three receipt-named legacy DBN files were verified present (24 MB XNAS, 21 MB ARCX and 20 MB ESH3). This resolves access, not the substantive coverage gap.

The frozen SCC mirror also contains usable historical reference inputs. CRSP index-membership series `indno=1000500` produced 503 S&P 500 securities active on 2023-01-23; historical names mapped 503/503 tickers and the prior-close DSF supplied 503/503 price/share observations. The resulting normalized prior-close capitalization weights are an explicit proxy, not official float-adjusted S&P weights or exact SPY holdings. Raw membership and roster stay on SCC.

Authenticated Databento metadata established that `XNYS.PILLAR`, `XNAS.ITCH`, `ARCX.PILLAR` and `GLBX.MDP3` cover the event. `EQUS.MINI` begins on 2023-03-28 and `EQUS.SIP` returned `dataset_not_found` for this account. Therefore the executable package is a named three-direct-feed composite, not national NBBO. The fixed 116-request package quoted 213,316,336 records, 15,812,661,560 uncompressed billable bytes and USD 38.659188836815 with zero API errors; acquisition is directly to SCC.

## Consequence for the retained case

The old data remain useful only for checking post-10:00 behavior and code/schema compatibility. The new bounded package begins at 09:25 and includes NYSE status/statistics/imbalance, direct-feed BBO/trades, two tick-level cash dates and ESH3 across the event plus ten fixed normal sessions. It does not contain CTA/UTP SIP or a final official bust file; those limitations remain explicit in `SOURCE_AND_ORDER_MANIFEST.json` and `DATA_COVERAGE.csv`.
