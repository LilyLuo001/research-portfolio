# Development text handoff

The corrected core sample completed in Kunshan job `123584403`. It contains 69 cells, 10,075 A records, 30,225 sampled B records, 200 development keys, 200 disjoint evaluation keys, and an 80-key configuration subset nested in development. The incorrect all-B core from run `123582600` is superseded; its separately sampled 600 diagnostic keys remain usable.

The two regional materializations are complete and use the frozen `materialize_selected_text.py` exact locator check:

- Kunshan: 122 rows, 115 source files, 121 row groups.
- Wuzhen: 78 rows, 74 source files, 76 row groups; Slurm job `45867338` completed in 2 minutes 19 seconds.

Local private handoff directory:

```text
/Users/lilyluo/Documents/LinkUp_Research_20260924/analysis_transition_20260930/dual_source_execution_v2/linkup_sample/private/run-123584403/dev_text_adapter
```

Files handed to the measurement owner:

- `development_200_kunshan.text.csv`
- `development_200_wuzhen.text.csv`
- `config_compare_80_kunshan.manifest.json`
- `config_compare_80_wuzhen.manifest.json`
- `DEV_TEXT_ADAPTER_RECEIPT_PRIVATE.json`
- both `development_200_{region}.materialize_receipt.json` files

The CSV text column is `original_text`; `ORIGINAL_TEXT` is an equal compatibility copy. Canonical locator fields are `JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, and `RECORD_SOURCE_ROW`.

The sampler excluded 72 recoverable prior-review JOB_HASH values. A complete historical-review original-text set was not supplied to this handoff, so cross-key historical full-text duplicate checking remains `not_checked_no_complete_historical_text_set_supplied`. The measurement owner is responsible for merging the two CSVs, applying the frozen full-text digest rule, and constructing the limited 80-record diagnostic package. Evaluation labels remain unrevealed.
