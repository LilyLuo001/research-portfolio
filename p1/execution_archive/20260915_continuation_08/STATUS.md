# P1 checkpoint 08 — strict necessary-support analysis

Date: 2026-09-15. Decision: **HOLD_DATA** under the fixed pilot contract. This
checkpoint reaches the roadmap's Step-4 early-stop branch; it does not estimate
the sealed treatment effect, decode quotations, or claim empirical power.

## Decisive results

- W021's corrected pre-announcement holdings produce 39 uniquely mapped US
  common stocks with valid same-date share denominators and frozen H/M/L tiers
  of 13/13/13.
- The corrected W021 metadata census has 1,082 accounting-period/public-release
  keys. In both independently retained SCC detail families, 1,033 have at least
  two analysts, 23 have one and 26 have zero. The EPS-base and `usfirm=1`
  diagnostic counts are identical.
- Within W021 high and low tiers, analyst support is strong: H PRE 182/198,
  H POST 109/124, L PRE 205/208 and L POST 113/122. The implementation-date
  boundary is preserved separately rather than placed in POST.
- W002's only currently proposed-clean high candidate fails the analyst gate in
  both complete SCC families: zero of three PRE and zero of one POST keys have
  at least two analysts. Removing `usfirm=1` does not change that result.
- W021 remains blocked from the frozen RTH/RTH-60 design because the archive
  manual and source-clock evidence do not certify the timezone/session meaning
  of `actu_epsus.anntims`. Repaired-roster competing-conversion eligibility is
  also not complete. Therefore quote measurement, PRE calibration, numerical
  rank and power were correctly not run.

Read the [decision](artifacts/strict_early_stop_analysis_20260915/DECISION.md),
[independent final review](artifacts/strict_early_stop_analysis_20260915/REVIEW.md),
[tier/side support aggregate](artifacts/strict_early_stop_analysis_20260915/w021_analyst_support_by_tier_side.csv),
and [execution receipt](artifacts/strict_early_stop_analysis_20260915/EXECUTION_RECEIPT.json).

## Single next action

Build one versioned, outcome-blind clock projection for the fixed W021 release
keys with authoritative timestamp semantics/timezone, bounded uncertainty,
historical XNYS open/close and RTH/RTH-60/UNKNOWN flags. If it yields common
H/L PRE/POST session support, return to the remaining Step-4
competing-conversion, common-calendar-cell and control checks before quotes.

Licensed row-level metadata remains on SCC. Git contains only safe aggregates,
code, documentation and receipts.
