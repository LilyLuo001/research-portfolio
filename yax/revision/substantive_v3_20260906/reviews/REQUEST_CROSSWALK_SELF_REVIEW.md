# Atomic request crosswalk self-review

Review role: execution-agent self-review, not independent scientific review  
Reviewed: 2026-09-06

`ACCEPTANCE_CHECK_CROSSWALK.csv` is generated from the supplied immutable
`requirements_seed.json`; it contains all 99 parent requirements and expands
their 297 acceptance checks into separately addressable atomic rows. Each row
retains all supplied source references, dependencies, priority, empirical
status, and whether a `P0:` inherited request is implicated. No inherited task
is silently retired: the default disposition explicitly points back to the
working status ledger.

The controlling prompt, both current referee reports, the earlier referee
report, the previous execution prompt, and the assistant audit were opened in
full before this check. The seed is the package's supplied cross-document
request map. This review verifies faithful expansion of that map; it does not
represent a second independent legalistic interpretation of every sentence in
the reports. It is therefore an acceptance-check map, not yet the source-text
request crosswalk required to verify G02. `SOURCE_REQUEST_REGISTRY.jsonl` must
add exact source-text hashes and resolved line locators. Any later-discovered
compound request must be added as a child amendment without changing or
deleting the supplied seed row.
