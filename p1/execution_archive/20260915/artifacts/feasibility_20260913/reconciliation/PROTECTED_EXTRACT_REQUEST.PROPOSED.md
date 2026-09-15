# Protected extract request — PROPOSED, not authorized

**Status:** `PROPOSAL_NOT_PI_APPROVED`. This is a manifest for a future row-filtered protected view after the reconciled contract is signed. It does **not** authorize an SCC job, data purchase, raw export, treatment-response calculation, or outcome access.

## Purpose and allowed stage

The permitted first stage is design eligibility and protected pre-treatment/untreated calibration only. It may establish the announcement/implementation calendar, PRE-exposure eligibility, SUE construction, session/horizon coverage, control/overlap membership, sponsor/dependence metadata, and pre-treatment noise/covariance calibration. It must not calculate, return, plot, rank or select on post-implementation high-vs-low response coefficients or response curves.

## Required inputs and minimum fields

| Asset / role | Minimum fields | Time / row restriction | Status |
|---|---|---|---|
| Verified conversion calendar | package/wave ID; constituent fund/series IDs; announcement source, date/time/timezone and uncertainty; legal effective and first ETF trading date/time; source accession | All registered candidate conversions needed to identify overlap, through audit date | `PENDING_METADATA` |
| PRE holdings / denominators | wave, fund, stock security ID, holdings as-of date, filing/publication date, split factor, shares, shares outstanding, denominator date, mapping status | Strictly before earliest verified announcement; retain later-public filing indicator separately | `PENDING_METADATA` |
| Identifier / sponsor view | point-in-time stock IDs, economic sponsor crosswalk and signed provenance, corporate-action mapping | Contract population and clean-control calendar | `PENDING_METADATA` |
| Earnings / forecast view | point-in-time identifier link; actual EPS/date/time/timezone; analyst forecast ID/time, fiscal period, estimate; currency/share/accounting basis | Issuers in frozen exposure universe plus contract-defined clean controls; 2019-01-01 through 2026-08-31 unless final calendar changes the window | `PENDING_METADATA` |
| Quote / session coverage metadata | symbol/date, bid/ask timestamps, quote state, exchange calendar/half-day flag, coverage indicator; SPY availability | Only candidate earnings windows and reference pre-treatment/untreated calibration windows | `PENDING_METADATA` |
| Daily beta inputs | stock and SPY price returns `RETX`, trading dates, corporate-action/distribution flags | `[−250,−21]` trading days per eligible earnings event; return only rows required for beta/calibration | `PENDING_METADATA` |

## Permissions and filters

- The request is limited to the frozen exposure population (currently 8,801 old-clock primary-ready stock-wave cells) and a contract-defined clean-control risk set. That count is a size-planning upper bound, not a new-clock eligible count.
- Announcements, exposure/as-of/publication timestamps, session coverage, SUE/forecast eligibility, controls and sponsor metadata are permitted **metadata** only when the PI signs the contract and protected-view authorization.
- Calibration responses may use only earnings windows strictly before each stock's earliest relevant conversion announcement, or genuinely untreated observations under the signed calendar rule. The extraction code must prove the row filter before opening response values.
- Post-implementation rows may provide non-response coverage/mask metadata only if the PI grants that narrow permission. They cannot include CAR, quote-return, response, coefficient, p-value, ranking, or model-selection fields.
- No automatic fallback to daily, OHLC, macro, ETF, five-second, or legacy paired-bar data is permitted.

## Required freeze before sealed analysis

The protected view must produce, without response values: new-clock high/mid/low tiers and absolute dose gaps; wave eligibility/rank preconditions; announcement/implementation/transition classification; session counts and common-horizon masks; control reuse; signed sponsor counts; dependency graph/component diagnostics; and the documented bootstrap-choice record. These metadata may complete data-dependent contract fields only under the PI-signed outcome-independent algorithms. They must be frozen and hashed before a separate sealed confirmatory response run.

## Explicitly blocked inputs

The request cannot proceed until the PI signs the reconciled contract and grants a protected-view authorization. It remains blocked if announcement timestamps, point-in-time identifiers, live bid/ask status, SUE basis, sponsor crosswalk, or the dependency/overlap calendar cannot be supplied. H3 decomposition is outside this extract unless its separate formula and permission are approved.
