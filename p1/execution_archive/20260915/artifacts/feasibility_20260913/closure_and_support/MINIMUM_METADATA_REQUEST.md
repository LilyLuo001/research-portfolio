# Minimum metadata request for support and dependence closure

**Status:** BLOCKED — local `SUPPORT_CENSUS.csv` records explicit
`NOT_AVAILABLE` rows; `DEPENDENCE_CENSUS.csv` records `NOT_AVAILABLE` rows plus
one explicitly `NOT_IMPLEMENTED` interpretation row. Existing permitted
artifacts describe exposure and part of the conversion calendar, but cannot
establish the requested session, clean-control overlap, or economic-dependence
counts without inventing a session rule or an inference rule.

## Scope and authorization boundary

This is a metadata-only request, contingent on (1) PI signature of the
reconciled estimation contract and (2) a protected-view authorization.  The
proposed request is not itself authorization for an SCC job, remote pull, data
purchase, raw export, or sealed outcome access.  The custodian should return a
row-filtered protected view or aggregate census, with a schema receipt and
SHA-256 manifest; no raw licensed rows are to be committed to this repository.

Candidate population: the frozen exposure universe represented by
`p1/conv_exposure_free.parquet` (stock × wave cells) plus the contract-defined
clean-control risk set.  Candidate calendar scope: all registered conversion
candidates needed to determine overlap through the audit date.  Candidate
earnings/coverage scope: issuers in that frozen exposure universe and clean
controls from 2019-01-01 through 2026-08-31, unless the final signed calendar
changes that window.  PRE holdings/calibration rows must be strictly before the
earliest verified announcement for the relevant stock; post-implementation rows
may supply only non-response coverage masks if that narrow permission is
explicitly granted.

## Smallest inspected permitted inputs

| Input | Why its provenance is established | SHA-256 | What it contributes | Why insufficient |
|---|---|---|---|---|
| `p1/conv_exposure_free.parquet` | Its lineage sidecar identifies it as the P1 free-path ConvExp output; its schema contains stock identifier, wave, effective date, dose, fund count, and source-accession fields. | `350c3c7aed6d1bf047a8970f4d5940f37f1ec89e012876cb0f081668a5d2b4e7` | Exposure stock-wave membership and dose fields. | No announcement time/timezone, earnings event metadata, quote/session coverage, controls, or sponsor identity. |
| `p1/conv_exposure_free.parquet.lineage.json` | Direct provenance sidecar for the permitted exposure output. | `ff26b812b5849825d9df0aa6b98815066564739596b2413c09b28656f89d116a` | Input/output provenance pointer only. | Does not add session, overlap, or dependence fields. |
| `p1/t2_wrds/waves.csv` | `p1/t2_wrds/README.md` identifies waves artifacts as committed public-T1-derived output, not licensed rows. | `f2ac39effe6040f566146303b8dc3976fbdfd56f7a78ed5e3a4c0c63391ff990` | Wave IDs, effective dates, number of funds, anchor marker. | No verified announcement metadata or event/session/control information. |
| `p1/t2_wrds/waves_members.csv` | Same documented public-T1-derived waves artifact. | `f080815ccbadf9df26b749bb2cba99cd22717e831d2ccdce94c32944945a5bf6` | Fund/series labels, family labels, effective-date and public-accession locators. | Family label is not a signed economic-sponsor crosswalk; no stock/control/earnings/session linkage. |
| `p1/t2_wrds/README.md` | Policy/provenance documentation for the preceding wave artifacts. | `e379ef1694a9087703023ad2ffa5c10008be339e9f6a8ca57564d4bc813dce0d` | Confirms public/derived status and licensed-data restrictions. | Documentation, not census rows. |
| `reconciliation/PROTECTED_EXTRACT_REQUEST.PROPOSED.md` | Bounded proposal that lists required metadata and exclusions; it explicitly says `PROPOSAL_NOT_PI_APPROVED`. | `9387846ee12e9865fd0abd012b20f1f0e941bce6a646af6265a9a5b17630589d` | Defines requested fields, scope, and permission prerequisites. | Is not an approval and contains no extract. |

Only parquet schema metadata and CSV header metadata were inspected for the
three tabular permitted inputs.  No outcome, earnings-response, quote,
forecast, actual-EPS, or other sealed source was opened.  No remote/SCC action
was performed.

## Required protected metadata fields

### A. Calendar and identifiers (support eligibility)

For every candidate package/wave and constituent fund/series, provide:

- package/wave ID; constituent fund and series IDs; announcement source
  accession/locator; announcement date, time, timezone, and uncertainty flag;
  legal-effective and first-ETF-trading date, time, timezone, and source
  accession;
- point-in-time stock identifier links and corporate-action mapping; and
- a contract-defined clean-control membership flag and exclusion reason.

For each frozen exposure component used to construct a proposed tier, also
provide holdings as-of date, filing-publication date, split factor/provenance,
shares held, shares outstanding, denominator date/provenance, mapping status,
and an explicit pre-announcement eligibility/missingness flag. The protected
view—not this local checkout—must calculate the new-clock positive ownership,
tie-preserving tercile cutpoints, high/middle/low tier and absolute high-low
dose gap using the signed algorithm. It must return tiers/dose-gap metadata and
reason codes, never returns or responses.

These fields are needed to classify each observation as PRE, transition,
post-implementation, or clean control.  Existing `effective_date` is not a
substitute for a verified announcement timestamp, so a session cannot be chosen
from it.

### B. Earnings/event and quote-session coverage (support census)

For every candidate earnings window only, provide metadata without any response
values:

- stable event ID; point-in-time stock ID; earnings announcement date, time,
  timezone, and timing-quality/uncertainty flag;
- exchange/calendar identifier; trading-date and half-day/holiday flag;
- deterministic session classification under the signed contract; requested
  horizon availability mask; bid/ask timestamp-presence and quote-state flags;
  SPY availability flag; and
- every response-leg calendar date contributing to 5m, 15m, 30m, 60m, close,
  and `+1d`, including the actual trading date used for the `+1d` leg; and
- SUE/forecast eligibility metadata only: forecast ID/timestamp, fiscal-period
  identifier, currency/share/accounting-basis compatibility flags, and an
  eligibility/missingness reason.  If actual/forecast values are needed to
  construct eligibility, construct it inside the protected view and return only
  the boolean/reason, never values.

The signed contract must fix the session mapping and horizon rule before this
view is run.  The census must report candidate event count, eligible count, and
each exclusion count by wave, tier, calendar classification, and reason, plus
common-horizon intersections for the comparison groups.  It must also emit a
row-level opaque event key only if needed for reproducible deduplication;
otherwise aggregates suffice.

### C. Exposure overlap and control reuse (overlap census)

For the frozen exposure population and clean-control risk set, return only:

- opaque stock key, wave ID, calendar classification, frozen tier/dose-bin,
  and eligibility flags;
- observed-support flags (not fitted predictions) for every positive-weight
  stock × calendar cell, plus the industry identifier and calendar-quarter
  identifier needed to audit the declared stock-by-wave and
  industry-by-calendar-quarter slope functional;
- repeated-stock/wave membership counts, treated-versus-control overlap flag,
  and control reuse count; and
- counts/cross-tabs required to identify empty cells and common support.

The view should calculate these using the PI-signed, outcome-independent tier
algorithm and output counts by tier × wave × support mask, not post-event
returns or statistics.

### D. Economic dependence (dependence census)

For all retained candidate stock/event rows and conversion entities, provide:

- opaque stock key; wave/package key; issuer ID; fund/series ID; and a signed
  point-in-time economic sponsor/group ID;
- provenance locator, effective-from/effective-to timestamps, mapping-status,
  and ambiguity flag for every sponsor/corporate-action mapping; and
- aggregate graph diagnostics: unique issuer/fund/sponsor counts, max cluster
  size, component count/size distribution, repeated-stock and repeated-issuer
  counts, and cluster intersections with treatment tier and clean controls.

`family` in the public waves file must not be silently promoted to the economic
sponsor cluster: the signed crosswalk, its point-in-time validity, and its
provenance are missing.

## Required census outputs and reproducibility receipt

After authorization, the custodian should supply either a protected aggregate
`SUPPORT_CENSUS.csv` and `DEPENDENCE_CENSUS.csv` or a metadata-only view from
which the repository can reproducibly build them.  Include a machine-readable
receipt with source/view hashes, query/view version, pull date, candidate and
retained denominators, field dictionary, exclusion-reason dictionary, signed
contract hash, authorization reference, and the exact pre-treatment/untreated
row filter.  The receipt must attest that no response field was returned.

## Explicitly excluded fields

Do not return or expose actual EPS, analyst forecast values, forecast errors,
SUE values, prices, returns, quote prices/sizes, spreads, CARs, response curves,
post-implementation response coefficients, standard errors, p-values,
rankings, or model-selection outputs.  No daily/OHLC/macro/ETF/five-second or
legacy paired-bar fallback is authorized by this request.

## Why a local census is not reproducible now

The currently permitted inputs can enumerate exposure cells and public
effective-date/fund metadata, but they cannot determine whether an earnings
event belongs to a signed session/horizon, whether it has compatible forecast
metadata, whether it is PRE/untreated under an announcement clock, which clean
controls overlap, or which economic-sponsor cluster captures dependence.
Producing a support/dependence count anyway would require unapproved session,
control, or clustering assumptions and would be non-reproducible against the
future protected view.  This request therefore fails closed.
