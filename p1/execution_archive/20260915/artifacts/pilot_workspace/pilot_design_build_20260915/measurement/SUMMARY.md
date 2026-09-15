# P2 measurement interface — prepared, not run

This directory implements the bounded, pure-metadata clock/session adapter. It accepts only a manifest, a custodian-supplied release uncertainty projection, and a calendar projection. It never reads native quote files, calculates returns, SUE, EPS, or prices, or upgrades source-clock candidates into release certification.

## Local result

The existing union-V2 manifest has 852 rows. Strict clock/session classification is `UNKNOWN_FOR_ALL_852`: the current evidence has neither a source-specific full-population timezone/first-release guarantee nor uncertainty bounds. The existing calendar (`7a791bb56ce116ddc196d40bb2b7eb2a8b2a4b333e1377d582c7c6162e26b770`) has only `calendar_basis,session_date`; it lacks `calendar_id,calendar_timezone,open_local,close_local`, so no source-clock-session-if-Eastern calculation is possible without inventing a session calendar. The prepared diagnostic instead contains 31 source-clock time-of-day bins (all 852 associations: 568 PRE and 284 POST) with no market-session labels.

The core-map intersection identifies 13 current-manifest candidate associations: 12 CRD associations require the already mapped Class-B repair to restore their existing core stock legs, and 1 GDEN association requires the existing transport gap to be retried. These are candidates only: final eligibility is not certified, no retry/purchase is authorized, and the SPY row attached to the GDEN failed job is preserved as a separate non-stock gap.

## Verification

`test_measurement_input_adapter.py` exercises 16 synthetic cases, including exact cutoff equality, open/close crossings, a UTC-source/Eastern-calendar conversion, missing intervals, duplicate calendar keys, multi-date intervals, conflicting calendar zones, and ambiguous/nonexistent DST times. All pass. These tests certify interface behavior, not the empirical release clocks. Final code hashes are recorded in the root execution receipt.

## Exact next operation and authority fit

Do not rerun the existing eight-column actuals projection: it already covers the 852 associations and cannot create a first-public-release guarantee or an error bound. The exact missing inputs are (1) a source-specific, supported uncertainty-policy/record with `source_id,source_timezone,interval_lower,interval_upper`, and (2) a versioned calendar projection with `calendar_id,session_date,calendar_timezone,open_local,close_local`. Return only interval/session classifications, aggregate counts, and a receipt. The existing eight-column bridge is insufficient for quote masks; it conveys no authority to decode native quote files, export raw values, scan archives, buy data, or access POST responses. The historical named-custodian proposal for PRE-only calibration / POST non-response mask remains a later approval condition, not present authority for those computations.
