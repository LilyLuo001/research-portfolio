# Stage C compact V1

This is a bounded storage trial for the frozen V5 parser. It does not change or
validate parser semantics. Four Parquet tables retain one row per ad, sparse
evidence, unresolved relation candidates, and raw-source locators/fingerprints.
Normalized text and full candidate JSON are omitted. Exact text slices are
reconstructed from the raw `DESCRIPTION` through the frozen V5 normalization
function and checked against the stored normalized fingerprint and offsets.

Every source row remains represented, including no-candidate, parser-error, and
truncated rows. `IS_APPLICANT_QUALIFICATION_CANDIDATE` remains presence;
`IS_APPLICANT_REQUIREMENT` remains strength/unconditional-path evidence.
Relations remain unresolved candidates, including OR paths.

Each input writes into its own immutable directory and ends with
`CHECKPOINT.json`. A cap stop occurs only before a row batch is written and
records `next_source_row` and `pending_rows`; committed rows are retained.
Per-input caps partition the global 250 MB Parquet output-plus-temporary
allowance; the runner reserves 1 MB within that cap for identities and receipts.
