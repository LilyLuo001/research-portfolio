# V3 pilot evidence boundary

The canonical private V3 pilot bundle is stored only at:

`/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3/pilot`

## Public Git artifacts

- `PILOT_PUBLIC_RECEIPT.json` is a redacted, non-row-level summary of the
  checkpoint status and bindings.
- `pilot_input_files.json` is the non-row-level input-provenance ledger.
- This README explains the evidence boundary.

The public receipt is informational only. It is not an authorization artifact,
and a fresh checkout cannot use it to authorize a full run.

## Private SCC-only artifacts

The following files are licensed, row-level, or detailed validation evidence
and remain untracked on SCC:

- `PILOT_PASS.json` or `PILOT_FAIL.json`
- `etf_flag_history_audits.json`
- `golden_case_results.json`
- `pilot_exposure_observations.csv`
- `pilot_invariants.json`
- `pilot_raw_trace_inspection.csv`

The private `PILOT_PASS.json` is the canonical authorization receipt, not a
research specification. It is valid only when the complete private evidence
bundle is present beside it and all frozen code, configuration, data-contract,
golden-sample, manifest, and artifact bindings match.

The sole executable normative contract is the three-file machine bundle in
the parent directory: `data_contract.json`, `gate01_config.json`, and
`golden_sample_spec.json`. Human documentation is explanatory only and cannot
change those rules.

No licensed row or licensed row value belongs in Git or in public prose. The
V3 checkpoint did not submit a full Gate 0/1 rerun, and Gate 2 remains
disabled.
