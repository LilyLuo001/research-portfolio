# Independent Stage-A diagnostic review

Date: 2026-09-21. Disposition:
**`PASS_TO_RUN_BOUND_DIAGNOSTIC_ONLY; NOT_EMPIRICAL_RELEASE`**.

The reviewed 29-file manifest contains 20,293,836 bytes: all files have checked
`bbo-1s` headers and content hashes, comprising seven files for each of four
venue datasets plus one `EQUS.MINI` file. It is a support-gap inventory, not
balanced event coverage: UNH has no candidate; QQQ mappings occur only in the
nine legacy XOM files; Microsoft has overlapping full-day and partial files.
Those remain file-source cells, not unique event support or NBBO.

The projection now verifies DBN hashes, schema/dataset, header intervals,
date-effective mappings, manifest/contract binding and the pinned `BBOMsg`
type. It uses `ts_recv < anchor` for baseline and `<= target` for later
endpoints, reports per-target header coverage, nulls all state fields for
ambiguous same-timestamp records, and reports skipped files explicitly. It
exports booleans, flags, age bins, publisher IDs and counts only—no quote
levels, sizes, returns, directions, response estimates or p-values.

Execution is approved only after an `APPROVED_DIAGNOSTIC_ONLY` release binds
the exact hashes below. Results cannot certify continuous live quotes, select
clock variants, establish common basket support, or authorize primary
analysis. Corrected holdings counts were separately checked against the frozen
32-event/eight-issuer roster (QQQ 16/32 and SPY 32/32 ticker-group membership),
but remain monthly-snapshot diagnostics, not point-in-time actual baskets.

```text
e5d120000de850c8ac0f1abc0e724875c086ba8142238e85747bcd7b23ebad91  DIAGNOSTIC_CONTRACT.json
8dd238099014900225287820aacfa768dbf7a0be23386afaa3e7988f7674bfed  data/QUOTE_INPUT_MANIFEST.json
876d81fdff0c725936ac80738b3c04fd84ba991cecd94d93289c380e94c0c7c1  data/quote_state_diagnostic.py
```

Requested Sol/high routing was accepted; backend telemetry is `NOT_OBSERVED`.
