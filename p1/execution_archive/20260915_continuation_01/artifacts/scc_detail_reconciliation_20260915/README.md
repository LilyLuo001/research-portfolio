# W002 high SCC detail reconciliation

The existing frozen `select_targets()` selector was applied before any source
Parquet read: exactly four event keys (one candidate; PRE=3, POST=1). A single
bounded pass over 2019–2021 core `ibes_detu_eps` and rescue
`ibes_allcols_detu_epsus` used only `cusip`, `fpedats`, `analys`, and `anndats`.
For each frozen key, metadata rows were counted in the protected
`[release_date-90 days, release_date)` window. Both source families produced
the same aggregate result: 3/4 keys observed, 4 rows total, analyst-count
histogram 0:1 and 1:3. No raw values or identifiers were emitted; row-level
inputs remain on SCC. The earlier broad W002/high attempt is explicitly
invalid and excluded.

The saved script replicates the existing frozen selector rather than importing
the original function. A single-CUSIP assertion was added after the observed SCC
run; the revised script was not rerun on source data. Seven in-memory synthetic
tests of the revised script passed (see `EXECUTED_TEST_RECEIPT.json`), including
date-window boundaries, distinct analyst handling, period mismatch and ambiguous
CUSIP rejection. This is implementation verification, not a research gate or a
claim of complete source-row identity. Multiset comparison remains NOT_RUN.
