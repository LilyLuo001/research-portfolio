# Linkage v1 real-input pilot

The bounded real-input pilot completed on Kunshan as scheduler job `123554098`
in 71 seconds. A deterministic `JOB_HASH` prefix selected 15,254 canonical ads
from the conserved 252,301-row fixed-three-shard key projection.

Records cardinality was exactly one for all 15,254 ads: zero unmatched and zero
multiple matches. No `COMPANY_ID` was null. The raw Records left join and the
aggregate denominator both conserved 15,254 rows, and none of the matched
Records rows lacked `CREATED`. The three input source files remained distinct.
`COMPANY_ID` remains a
company-scrape entity identifier and is not interpreted as a parent company,
establishment, or stable firm.

The O*NET lookup read the complete delivered snapshot identity: 62 files and
356,299,258 footer rows. It produced 15,248 official O*NET-SOC 2019 members,
3 `99-9999.00` placeholders, 3 missing keys, no blank codes, no other
nonmembers, and no duplicate keys. Its raw left join also conserved 15,254
rows. These are snapshot assignments, not historical occupation evidence.

`BASE_HASH` and `TITLE` coverage are explicitly unmeasured because the reused
Records index omits those fields. JOB_HASH disagreement after a
`RECORD_SOURCE_ROW`-only match is also unmeasured in this hash-partitioned
pilot. Remote data were not joined. The machine-readable report therefore
accepts the executed company/occupation linkage while preserving these scope
limits.

The Records `hash_prefix=0` scope is complete for the pilot selection: the
frozen index builder routes valid hashes by their lowercased first hexadecimal
character. The receipt records the builder digest. The superseded successful
job `123553191`, its aggregate report, and its exact executed source are kept
as separately named provenance artifacts.
