# Linkage v1

`RULES.json` freezes the first Records/company/O*NET linkage. The executable
emits aggregate coverage only and deliberately excludes Remote. `COMPANY_ID`
is retained only as a scrape-entity field; it is not interpreted as a parent
company or stable firm. O*NET is a delivered snapshot classification, not a
historical assignment.

The pilot accepts key-only `ad_status` projections plus narrowly selected
Records and O*NET Parquet inputs. Its report conserves the canonical ad
denominator and separates Records 0/1/>1 cardinality and five O*NET membership
states. `linkage_accepted` is false if either source can multiply ads; aggregate
regrouping conservation is reported separately from raw left-join conservation.
A hash-partitioned narrow pilot cannot audit JOB_HASH disagreement
after matching only `RECORD_SOURCE_ROW`; that audit remains explicitly marked
unmeasured rather than silently reported as zero.

The completed real-input pilot is in `results/PILOT_COVERAGE.json`, with run
identity in `results/RUN_RECEIPT.json` and a concise interpretation in
`results/RESULTS.md`.
