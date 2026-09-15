# Saved-output verification

2026-09-15. Executed `verify_saved_aggregates.py` using the bundled local Python.

- The five aggregate-file hashes and executed code/config/manifest hashes match the saved full receipt.
- Independently summed saved aggregate tables: 99 candidates, 27 all-clock PRE/POST pairs, 2 nominal-clock pairs, 19 all-clock observed-min2 pairs, 0 nominal observed-min2 pairs. The 1,151 analyst keys reconcile to 525 observed-min2 plus 626 unknown; 35 nominal keys include 1 observed-min2.
- Re-executed the nine existing clock/analyst-window fixtures: PASS.
- No SCC source rows were re-read by the coordinator. This is aggregate verification, not an independent data-referee review or a scientific gate PASS. Several upstream receipt invariants are declarative booleans, not separately executable source-level tests.

`conversion_status=UNIQUE_VALID_PERMNO_SOURCE_ROW` describes security-link uniqueness, **not** competing-conversion cleanliness. The aggregate `has_nonunique_source_row_status=False` likewise does not establish absence of competing conversions. Competing-conversion eligibility remains UNKNOWN for this sidecar. Do not promote any of these columns to a clean-sample flag.

The spreadsheet skill informed the read-only check of column units, source lineage and missing-versus-zero semantics. No spreadsheet inputs were edited.
