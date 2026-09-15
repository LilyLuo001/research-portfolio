# Further verification results — 2026-09-15

**New result: CRD repair symbology validated across all 192 requested windows; all four failed cost/count queries now succeed. Measurement Gate 1 remains NOT PASSED.** No market data downloaded and no new data spending in this turn.

## Executed vendor checks

Used the owner's previously explicit authorization to supply the provided credential to a temporary process environment. The credential was not written to a repository or credential file. The allowlisted scripts invoked only `symbology.resolve`, `metadata.get_cost` and `metadata.get_record_count`. No timeseries, batch, live or Reference purchase endpoint was used. The prior `AUTH_ENV_ABSENT` result remains historical; it is no longer the blocker for these executed checks.

| Dataset | Verified request symbol | Repair windows mapped over every touched UTC date |
|---|---|---:|
| XNAS.ITCH | CRD.B | 48 / 48 |
| BATS.PITCH | CRD.B | 48 / 48 |
| ARCX.PILLAR | CRD B | 48 / 48 |
| XNYS.PILLAR | CRD B | 48 / 48 |

All four API responses have empty partial/not-found lists. The checker validates each date touched by each half-open request window, including UTC-date crossings, rather than checking only the starting date. It permits instrument IDs to change between dates and requires one ID per covered date. This validates the proposed native-symbol repair in conjunction with the previously verified historical Class B identity. It does not prove usable live quotes or replace the missing CRD DBN records.

The exact original four failed requests were rechecked without changing their parameters:

| Job | Current estimated cost USD | Record count |
|---|---:|---:|
| ALTJOB_00186 | 0.012025535107 | 40,351 |
| ALTJOB_01420 | 0.004295706749 | 14,414 |
| ALTJOB_01748 | 0.000643432140 | 2,159 |
| COREJOB_00366 | 0.011890828609 | 39,899 |

All eight cost/count calls succeeded. Total for those original request parameters is **USD 0.028855502605**, not charged. **This is NOT the total price of the CRD repair:** ALTJOB_01420 still contains bare CRD in its unchanged original symbol list, and grouped record counts do not certify every symbol. Final corrected repair pricing must separately cover the validated 192 CRD windows and omit duplicate companion symbols. These four quotes establish transport recovery, not completed acquisition or per-symbol quotation coverage.

## Clock verification advanced, not silently approved

Located the manufacturer's November 2013 Detail History manual: page 15 documents season-dependent Eastern/Daylight time; page 57 distinguishes activation and announcement time. The Summary manual pages 19/26 connects the post-2013 actuals files and their timestamp layout. This is meaningful new source evidence, but the Detail guide explicitly covers direct deliveries rather than third-party platforms. Applicability to the WRDS `actu_epsus` delivery in 2019–2024 and the first-release/rounding contract are not certified solely by this manual.

Checked the only two pre-existing public issuer locators that overlap the current PRE population. Both Oracle pages loaded, but the checked HTML meta/time/JSON-LD fields provided no publication timestamp. No agreement was invented from date-only pages. Results and the source citations are in `clock_sources_v2/CLOCK_EVIDENCE_V2.md` and its receipts. No article body or financial values were exported to the report.

## Remaining next action

The binding scientific step is now **WRDS actuals clock bridge and release-accuracy validation**, not authentication or an unidentified CRD class. Obtain source-specific confirmation of the Eastern/DST convention, rounding/imputation and report-versus-first-public-release semantics for the named fields, or original publication-time evidence for the fixed events. That is a bounded source question, not a new roster or whole-contract request. No message to WRDS/LSEG was sent without separate user authorization.

Once resolved, version the clock policy and run a small golden PRE endpoint test before the full six-horizon stock/SPY mask census. Corrected CRD procurement remains a separately priced acquisition step; there was no permission expansion into new purchases or response analysis here. No power result, treatment effect or research GO is claimed.

## Evidence files

- `free_symbology_responses.json`: four actual free API responses.
- `repair_mapping_validation.csv`, `repair_mapping_receipt.json`: 192-window interval checks.
- `four_quote_recheck.json`: exact saved cost/count responses.
- `clock_sources_v2/public_metadata_candidates.json`: two public-source check outcomes.
- `verification_v2_receipt.json`: current artifact hashes, scope and invariant checks.

No extra agents or whole-project review were launched; loops and validation used deterministic scripts.
