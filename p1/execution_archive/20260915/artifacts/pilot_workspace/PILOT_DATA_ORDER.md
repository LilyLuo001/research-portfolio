# P1: fixed conversion-matched quotation pilot

**Decision date: 14 September 2026. This is a concrete data order, not another request to design a sample.**

## Executive decision

Acquire a deliberately small, historical, two-cohort quotation-development sample: **8 named stocks, 32 named earnings releases, 2 focal conversion waves, and SPY**. Buy only the explicit disjoint windows in the supplied request CSVs. Do not download continuous 2019–2023 histories or the full 3,440-security universe. Do not add FOMC, futures, options or a new research branch to this purchase.

The primary feed is **XNAS.ITCH / bbo-1s**. Four pre-focal windows receive **XNAS.ITCH / mbp-1** validation. A limited **ARCX.PILLAR / bbo-1s** overlap is a secondary venue check. Optional IWM, DFAC and BSVO observations are last in the spending priority.

**Important scope decision:** accept Nasdaq-venue quotes for this development pilot. They are not the national/SIP NBBO. The pilot can establish source usability, session coverage and implementation behavior. It cannot certify the covariance, timing effect or power of the final market-wide P1 estimator.

The target gross quoted order is **at most $100**, leaving **$25 unspent reserve** out of the user's $125 credit budget. No exact account-specific quote has been obtained. The final executor must call the free cost endpoint for these exact requests, apply the preset reduction rule if needed, and never make commitments exceeding the confirmed remaining budget. This enforces the spending limit; it does not manufacture a vendor price.

## 1. Actual conversion links

| Cohort | Repository wave / effective date | ETF operation/listing date in issuer material | Conversion |
|---|---|---|---|
| Dimensional | W002 / 2021-06-11 | 2021-06-14 | Four predecessors became DFAC, DFUS, DFAS and DFAT |
| Bridgeway | W016 / 2023-03-10 | 2023-03-13 | Omni Tax-Managed Small-Cap Value Fund became BSVO |

Preserve the two date concepts. The Bridgeway issuer describes its reorganization on March 13; the repository stores March 10. The selected earnings dates are sufficiently far away that this discrepancy does not determine which side of the focal conversion they occupy. Neither date supplies the earliest public-announcement clock.

Repository basis: `LilyLuo001/research-portfolio` at commit `cb36417304b282cda5e38ede13d1af872ad9f346`, `p1/exposure/exposure_stock_wave_all.csv` (reviewed E007 SHA-256 `905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320`) and `p1/exposure/nport_crsp_security_crosswalk.csv`.

All eight proposed stocks are identified in the relevant predecessor-holdings crosswalk. W002 holdings are dated 2021-04-30 and W016 holdings 2022-12-30. This is **PRE-effective membership**, not a certification of PRE-announcement ownership or final tercile assignment. The purpose is selecting relevant securities to acquire, not silently approving the causal sample. The Bridgeway cohort also has earlier-conversion overlap; PRE-focal does not mean never treated.

Public conversion sources:
- Dimensional: https://www.dimensional.com/us-en/newsroom/dimensional-lists-four-new-etfs-following-the-industrys-largest-mutual-fund-to-etf-conversion
- Bridgeway: https://bridgewayetfs.com/bsvo/

## 2. Exact stocks and releases

All dates are acquisition dates in the issuer's U.S. release calendar. Public source locators and evidence categories are in `earnings_events.csv`. Subminute public-release timestamps remain to be verified before intraday response analysis. The acquisition design deliberately does not require the unresolved global ANNTIMS timezone rule.

| Wave | Stock / historical PERMNO | PRE-focal release dates | POST-focal release dates |
|---|---|---|---|
| W002 | JJSF — J & J Snack Foods / 10026 | 2019-07-29; 2020-01-27 | 2021-07-26; 2021-11-15 |
| W002 | PLXS — Plexus / 10032 | 2019-10-23; 2020-01-22 | 2021-07-21; 2021-10-27 |
| W002 | MSFT — Microsoft / 10107 | 2019-10-23; 2020-01-29 | 2021-07-27; 2021-10-26 |
| W002 | ORCL — Oracle / 10104 | 2019-09-11; 2019-12-12 | 2021-09-13; 2021-12-09 |
| W016 | SKYW — SkyWest / 10421 | 2021-10-28; 2022-04-28 | 2023-07-27; 2023-10-26 |
| W016 | AXL — American Axle / 86547 | 2021-11-05; 2022-02-11 | 2023-08-04; 2023-11-03 |
| W016 | AROC — Archrock / 92245 | 2021-11-01; 2022-05-09 | 2023-07-31; 2023-11-01 |
| W016 | BHE — Benchmark Electronics / 76224 | 2021-10-27; 2022-04-26 | 2023-07-31; 2023-10-25 |

Why these names: the first cohort includes two large technology-company comparisons and two other predecessor holdings, rather than only liquid mega-caps. The second cohort exercises a non-Dimensional conversion and different underlying firms, including pre-open and after-close release settings. This is purposive measurement sampling, not representative or matched-control causal sampling. No release was selected by an estimated price response or statistical significance. Public results pages used to verify dates may contain financial results; no such result is used as a selection variable.

W002 pre-focal dates precede the 2020 public conversion-plan period; W016 pre-focal dates precede the located 2022 proxy materials. Full anticipation/calendar and earlier-treatment eligibility still belong to the full P1 build. The currently signed RTH-only proposal is not being redefined by this procurement: non-RTH windows are diagnostic populations, not an automatically approved primary sample.

## 3. Exact quotation windows

For **each named stock and SPY**, use the following windows. D is the listed earnings-release trading date; D+1/D+2 mean subsequent U.S. equity trading days, not calendar days.

| Leg | New York local time | Purpose |
|---|---|---|
| Previous trading day | 15:40–16:10 | Prior close/baseline neighborhood |
| D | 04:00–20:00 | Capture either pre-open or after-close release without assuming its exact time |
| D+1 | 04:00–20:00 | Next opening, early adjustment and next close |
| D+2 | 15:40–16:10 | Additional terminal-close neighborhood for opening-anchored after-close constructions |

The CSVs provide **exact UTC start/end timestamps**, calculated using `America/New_York`; end bounds are exclusive. No fixed UTC−4 offset is used. The manifest includes the November 2021 DST transition. Actual selected days were checked as regular-close XNYS sessions using `exchange_calendars` 4.13.1; that is a schedule-construction check, not proof of historical feed availability.

The 32-event core consists of **220 disjoint single-symbol request intervals over 92 dates**, totaling **1,939 symbol-hours**. Its earliest requested date is **2019-07-26**, latest **2023-11-07**. Those bounds describe the outside envelope of the slices, NOT a continuous request. Common SPY intervals are unioned and purchased only once. `core32_event_request_map.csv` maps each required event leg to its purchased request.

Only the mapped event-specific intervals may be used for a given event's authorized analysis; a unioned file may contain another event's later prices. Do not allow caching/deduplication to bypass the pre/post analysis boundary.

## 4. Schemas and fields

**Core:** `XNAS.ITCH`, `bbo-1s`, `stype_in=raw_symbol`, unadjusted native DBN with its metadata. Retain all native fields. At minimum preserve:

- `ts_recv`, `ts_event`, publisher ID, instrument ID and schema;
- level-0 bid/ask price and size (`bid_px_00`, `ask_px_00`, `bid_sz_00`, `ask_sz_00` after DataFrame conversion);
- last-trade price/size and sequence/flags where present in the actual schema;
- instrument mapping, data-request interval, source dataset and successful-request receipt.

Do not invent unavailable fields, infer quote age from the last-trade timestamp, or treat OHLCV/TBBO as equivalent quotation samples. For interval BBO, `ts_recv` is the interval-end clock; `ts_event` concerns the last trade. An absent interval can reflect no update, so do not fill every gap as a new observed quote or discard all unchanged states. Inspect overlapping MBP-1 before committing to reconstruction rules. Request-start state and extended-session coverage need an empirical check on the downloaded sample; missing initial state remains missing.

**Validation, fixed in advance:** on each row below download stock and SPY in XNAS.ITCH `mbp-1`; the same stock/time windows in ARCX.PILLAR `bbo-1s` are secondary validation:

| Stock | Date | New York window |
|---|---|---|
| MSFT | 2019-10-23 | 15:30–18:00 |
| PLXS | 2020-01-22 | 15:30–18:00 |
| AXL | 2021-11-05 | 06:00–10:30 |
| BHE | 2022-04-26 | 15:30–18:00 |

This is eight MBP-1 and eight secondary-venue single-symbol intervals. No MBO, MBP-10, paid reference-data subscription, options or futures are required.

**Optional ETF bundle:** IWM over the same event legs; DFAC over W002 POST-focal legs only; BSVO over W016 POST-focal legs only. `extra_etf_requests.csv` has 138 unioned single-symbol intervals. No pre-conversion DFAC/BSVO tape is requested. Optional ETFs are for post-launch connectivity/measurement, not before–after ETF leadership.

## 5. Budget and purchase rule

| Allocation | Planning amount (NOT a vendor quote) |
|---|---:|
| Core 32-release stock+SPY one-second quotes | $70 |
| MBP-1 and limited second-venue validation | $20 |
| Optional ETF bundle | $10 |
| Unspent reserve | $25 |
| Total ceiling | $125 |

Exact cost is account-dependent and must be queried on these actual manifests. The public Databento credit illustration is not a quote for SPY or this order. No cost amount in this file is represented as measured.

**Fixed execution algorithm, before any charged action:**
1. Confirm the user's actual unused credit balance, expiry and license eligibility without displaying secrets or accepting new paid contracts. Use at most the lesser of $125 and the confirmed remaining credits; cash spending is zero.
2. Resolve all explicit historical symbols and per-schema date ranges. Quote every exact requested interval with the free metadata API; preserve unquoted/unavailable requests. Do not count an error as $0.
3. Price the full32 core and the fixed XNAS MBP-1 validation as one preferred base. If this base is <= $100 and fits remaining credit, select it. Planning allocations can shift between core and validation within that total.
4. Add the ARCX check first, then extra ETFs, only as complete quoted bundles while the total remains <= $100. Unused budget is not an instruction to add more data.
5. If the preferred base exceeds the cap, use the prespecified `core16_budget_reduction_requests.csv` plus the same MBP-1 validation. This retains all eight stocks, one PRE-focal and one POST-focal release for each. No lowest-price, strongest-response or post-outcome name selection is permitted. The reduction is only a purchase-scope reduction, not a final scientific sample choice.
6. If that smaller base also exceeds the cap, do not charge: report its exact quote and the shortfall. Do not exceed $125 or replace quotations with bars. Missing source availability for a required core symbol/schema is also a specific exception, not a license to choose a random other stock/feed.
7. Present a compact exact-cost receipt; with the owner's express bounded purchase instruction, complete the approved requests IN THE SAME RUN. Do not end with another generic preflight-only handoff. Without that instruction, provide the single exact order for approval.
8. Deduplicate intervals, cache native files, use documented batch re-downloads where practical, reserve the maximum price of in-flight orders and never blindly retry a potentially charged request. Verify a billing discrepancy before further requests. The $25 reserve is not permission to spend it on new scope. Record actual gross usage, not only cash charged after credits.

This procedure controls expenditure; the complete 32-release price has not been certified from this environment. No purchase was made when this package was created.

## 6. Companion research inputs (existing licensed sources, not Databento purchases)

For the exact 32 issuer-period observations request a small companion table inside the existing approved WRDS/SCC environment:
- event identifier, PERMNO, historical ticker/CUSIP validity and fiscal period;
- public release date, separately verified time/timezone and precision; call time separately;
- original actual/forecast identifiers and compatibility/coverage flags;
- for explicitly approved PRE-focal calibration only, consistent actual/forecast EPS and the prespecified surprise construction; do not open POST financial values by this order;
- corporate-action/dividend information for the actual endpoint intervals;
- the eight securities' wave membership, ownership as-of date, announcement date, implementation dates, and other conversion overlaps; final PRE-announcement tier may remain unknown.

Schema/source rules and existing protected-data permissions apply. Do not purchase these companion fields from a new vendor merely to finish this quote order. Date-wide downloading can proceed without resolving the global ANNTIMS timezone question. Exact intraday response analysis cannot.

## 7. What will be done with the result

First inspect the fixed pre-focal development windows: actual quote states, bid/ask paths, first-hour availability, schema agreement and venue sensitivity. Calibration involving earlier-treated W016 names is labeled source/measurement development, not untreated counterfactual covariance. Statistical calibration for a specific untreated P1 target requires its own eligible subset.

Download post-focal observations into a separate archive; no treatment contrast, response plotting or coefficient inspection is authorized without the owner's explicit analysis permission. Structural/file checks and coverage counts do not validate causal effects. Development events and any inspected outcomes must be recorded and excluded or disclosed appropriately in later confirmatory work.

Deliver native quote files under the data license, event-aligned pre-focal development summaries where permitted, a source coverage table, and actual spending receipts. This is a measurement/calibration pilot, not an estimator-correct final power calculation or an identified two-wave DiD. A Nasdaq-only null does not establish a national-market null.

## 8. Source register and verification limits

Each selected date has a public locator in `earnings_events.csv`; one Oracle PRE date uses the issuer's scheduled-release notice corroborated by an earnings-history listing; one JJSF PRE date uses a reprint of the issuer's wire release. These evidence levels are visible, not promoted to second-accurate public dissemination times. The executor can resolve an isolated source/date conflict from the cited release; it must not choose dates by price behavior.

Provider primary documentation:
- https://databento.com/pricing
- https://databento.com/docs/venues-and-datasets/xnas-itch
- https://databento.com/docs/venues-and-datasets/arcx-pillar
- https://databento.com/docs/schemas-and-data-formats/bbo
- https://databento.com/docs/schemas-and-data-formats/mbp-1
- https://databento.com/docs/faqs/difference-between-mbp-and-tbbo
- https://databento.com/docs/api-reference-historical/metadata/metadata-get-cost
- https://databento.com/docs/portal/billing

No source licenses, account entitlements, exact API costs, empirical quote quality or independent researcher signoff have been verified by this manifest-generation run. What was executed here: generation and deterministic verification of dates, disjoint intervals, duplicate benchmark reuse, exact UTC offsets and count arithmetic.
