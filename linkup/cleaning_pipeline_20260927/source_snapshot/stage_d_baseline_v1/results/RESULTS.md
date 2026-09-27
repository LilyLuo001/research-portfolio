# USA first-observed cohort × snapshot O*NET baseline

Job `123129172` completed successfully. All three output views conserve 253,210,047 USA records quarter by quarter.

- O*NET key matches: 253,127,252 (99.9673%).
- Format-valid nonblank codes: 253,123,825 (99.9659%). This is not official-taxonomy membership.
- Blank codes: 3,427; invalid-format codes: 0; missing O*NET keys: 82,795.

## Largest 2-digit groups, 2016 onward

| Code | Record count | Share |
|---|---:|---:|
| 29 | 24,624,944 | 12.334% |
| 41 | 24,344,866 | 12.194% |
| 11 | 23,904,257 | 11.973% |
| 43 | 18,819,703 | 9.427% |
| 13 | 15,392,656 | 7.710% |
| 53 | 12,564,869 | 6.294% |
| 15 | 11,721,124 | 5.871% |
| 35 | 10,193,772 | 5.106% |
| 31 | 8,636,180 | 4.326% |
| 49 | 6,869,768 | 3.441% |
| 51 | 6,738,930 | 3.375% |
| 25 | 5,459,959 | 2.735% |

Codes are current delivered snapshot O*NET assignments attached to Records first observed in each cohort. They are not point-in-time historical classifications, vacancy counts, technology adoption, or AI effects. The 2007 series begins in Q3; 2026 Q3 is partial through approximately 2026-09-06, so 2026 totals must not be compared directly with full-year 2025. Annual shares describe each year’s observable interval.

The subsequent official O*NET 2019 membership audit flags 45,752 records coded `99-9999.00` and 69 other nonmember codes. Use `../taxonomy_audit/quarter_full_code_flagged.parquet` for membership-aware analysis; raw aggregate outputs above remain unchanged. Official-member coverage is 253,078,004 / 253,210,047 (99.9479%).

## Acceptance and reproducibility

Independent reads of the three Parquet outputs found identical 77 year-quarter keys and identical denominators for every quarter. Each view sums to 253,210,047 records, and the production data contain zero USA records with a null `CREATED` value. The production code is frozen as `build_occupation_baseline_job123129172.py` (SHA-256 `95aa9e7c09cabc01f10d45a567f726b96468ae49cbdb562c99b115b422a3118b`).

The maintained implementation uses a window denominator that also preserves null-date groups. A 17-row DuckDB 0.9.2 fixture verified left-join conservation, missing/blank/invalid O*NET groups, and preservation of one null-date record. Its maintained-code SHA-256 is `7d749df1695a8443eab8c7776d1b9dae06a58b3fdd6194836356fc07eade42ec`. See `acceptance_validation.json` for machine-readable checks and output hashes.
