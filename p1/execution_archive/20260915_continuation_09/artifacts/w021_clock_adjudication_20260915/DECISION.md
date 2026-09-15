# W021 event-clock adjudication

## Question and boundary

Does the repaired W021 high/low roster have enough earnings-event support to
enter the frozen RTH/RTH-60 identification and power pipeline?

This is a necessary-support adjudication only. It uses metadata, an existing
analyst-count eligibility flag, provisional exposure tiers, and a versioned
exchange calendar. It reads no EPS or forecast values, prices, quotes, returns,
CARs or treatment outcomes. It does not select a session or infer a treatment
effect.

## Inputs and invariants

- Repaired roster: 39 U.S. common stocks, provisional high/middle/low tiers of
  13/13/13, established in continuation 08.
- Earnings-release projection: 1,082 W021 release keys.
- Analyst gate: release keys require at least two analysts.
- Calendar: complete XNYS sessions for 2019-01-01 through 2026-08-31,
  `America/New_York`, including historical early closes; SHA256
  `dd6fc11ab324f8e19fdd3ab977d6789ae099272ad32e3a75b8f6fa6845fc3562`.
- Frozen session rule: RTH release with at least 60 trading minutes before the
  actual close. The sensitivity run does not amend this rule.
- Hypothetical clock scenarios are diagnostics, not source certification.
- The 0–60 minute receipt-lag range is illustrative and not an empirically
  established error bound.

## Certified projection

The initial source-safe projection records valid exchange dates where possible,
but classifies all 1,082 release clocks as
`UNKNOWN_TIMEZONE_AND_PRECISION_UNCERTIFIED`. Consequently, certified common
RTH/RTH-60 support is zero by construction; this is an unknown-data result, not
evidence that every event was outside RTH.

## Clock sensitivity

The primary sensitivity run uses the complete XNYS calendar and the two-analyst
key filter. The decisive stock counts are:

| Scenario | H: >=1 PRE & >=1 POST | L: >=1 PRE & >=1 POST | H: >=8 PRE & >=4 POST | L: >=8 PRE & >=4 POST |
|---|---:|---:|---:|---:|
| Display as America/New_York | 0 | 0 | 0 | 0 |
| Display as fixed UTC-05 | 0 | 0 | 0 | 0 |
| Display as UTC | 7 | 7 | 6 | 7 |
| Eastern with first-public in receipt minus 0–60m | 0 | 0 | 0 | 0 |

An independently implemented secondary diagnostic was retained for audit but
is **not accepted as corroboration**. Its unfiltered clock-class counts differ
from the primary aggregate in ways not explained solely by the analyst filter
(for example, UTC low POST and Eastern high PRE). It also applies a containment
rule that is not directly comparable to nominal classification. The secondary
files are quarantined as `NON_DECISION_DIAGNOSTIC`; no count or conclusion in
this decision depends on them. A third implementation is unnecessary because
the primary source code, hashes and aggregate invariants are directly
reproducible and the unresolved source contract already triggers the stop.

The scenario flip is economically material. It is prohibited to choose UTC
because it yields support, just as it would be wrong to declare failure by
assuming Eastern without an authoritative bridge for the harvested table.

## Bounded public-clock rescue

A protected SCC-only manifest selected 24 boundary-sensitive keys from six
exposure-rank-selected stocks. One bounded issuer-IR/SEC/wire search round found
two public directional schedule statements (one “after market close,” one
“before market open”) but no exact, source-certified first-public timestamp or
release timezone. The two pages therefore cannot classify any of the 24 keys;
all remain unresolved. No protected row-level metadata was exported.

Manufacturer documentation previously archived for I/B/E/S Detail History
supports an Eastern/DST convention for direct delivery, but the archived review
correctly leaves the bridge to the harvested WRDS `actu_epsus` records unknown.
It also does not resolve whether `anntims` is first-public release, vendor
receipt, or activation, nor its precision/revision semantics. That documentary
evidence makes the Eastern failure scenario important, but not certified.

Databento quote data cannot repair this metadata contract. Quote timestamps
measure market records; selecting an announcement clock from the price response
would condition the design on its outcome. Generic corporate-action record
timestamps likewise are not a verified earnings first-public clock.

## Adjudication

**Current status: HOLD_DATA.** The sole unresolved fact changes the necessary
support verdict from zero to a potentially viable Stage-A sample. It must be
resolved from source authority, not chosen from the output.

Conditional consequences:

1. **Authoritative Eastern/DST plus adequate semantics/precision:** the frozen
   W021 RTH-only design fails the necessary support gate and becomes
   `HOLD_DESIGN`. Stop this estimator; a different session/estimand would be a
   PI amendment and a new pilot.
2. **Authoritative UTC plus adequate semantics/precision:** Stage A passes only
   as a necessary condition. Next test competing conversions, common calendar
   support, controls and dependence. Quotes/rank/power still do not follow until
   those gates pass.
3. **No authoritative bridge:** remain `HOLD_DATA`; do not spend more on quotes
   or estimate power.

## Exact next action

Request a versioned data-owner/provider answer specific to the full frozen
manifest coverage of the harvested `ibes.actu_epsus.anndats/anntims` delivery:
timezone/DST convention;
announcement versus vendor-receipt/activation semantics; precision, rounding
and imputation; and revision/correction rules. Reclassify the existing 1,082
keys with that answer and the already verified XNYS calendar. This is a single
metadata input, not a request for more price data or a new research plan.
