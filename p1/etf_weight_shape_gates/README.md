# P1 V3 data-contract checkpoint

## Checkpoint state

The canonical checkpoint is V3. Its SCC root is:

`/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3`

- All Gate 0/1 outputs produced before the V3 data contract remain
  `INVALIDATED_PENDING_DATA_CONTRACT`.
- The V3 work stopped at the targeted data-contract pilot checkpoint. No full
  Gate 0/1 rerun was submitted.
- Gate 2 remains disabled. Its retained launcher is fail-closed and exits
  without running Gate 2.
- No Gate 0, Gate 1, Gate 2, treatment-effect, outcome, or regression result is
  reportable from this checkpoint.

## Sole executable normative contract

Exactly these three machine-readable files jointly define the executable V3
research specification:

- `data_contract.json`
- `gate01_config.json`
- `golden_sample_spec.json`

They are the sole normative authority for execution. Human-readable research
plans, status notes, audit memos, READMEs, and documentation-evidence files are
explanatory only. If explanatory prose conflicts with the three machine files,
the machine files control and the prose must be corrected.

`pilot/PILOT_PASS.json` is a private, hash-bound authorization receipt. It
records whether the frozen specification and evidence passed; it does not add
to or amend the specification. `pilot/PILOT_PUBLIC_RECEIPT.json` is a redacted
public receipt and can never authorize a full run.

Any change to a formula, tolerance, date cutoff, mapping rule, counterfactual,
entity definition, source-field interpretation, availability rule, pro-rata
criterion, or registered scientific fileset is a specification amendment. It
requires a newly frozen golden sample and a new targeted pilot before a full
run can be considered.

## Required checkpoint sequence

Before any future full Gate run, the workflow must:

1. freeze distinct indices for pooled portfolio, share class, ETF security,
   underlying security, economic date, and availability timestamp;
2. verify the row unit of `market_val`, the units and same-date denominator of
   `percent_tna`, portfolio-level versus share-class-level TNA, and the dated
   portfolio-to-ETF-class relationship from documentation and raw records;
3. freeze the required golden-sample categories and exact input paths;
4. demonstrate the same-date `percent_tna` identity within the frozen
   tolerance where both sides are available;
5. permit ETF-class dollar scaling only for a date-verified pro-rata claim on
   the pooled portfolio;
6. run one small end-to-end pilot and reconcile at least twenty final
   observations to raw rows;
7. create the private `PILOT_PASS.json` only when every invariant passes; and
8. make the full-run preflight exit before archive discovery unless the
   private receipt and every frozen code, configuration, contract, manifest,
   and evidence binding match.

The pilot may open only the exact files registered in
`golden_sample_spec.json`; it may not glob or enumerate the holdings archive.
Passing the pilot does not override `full_run_enabled=false`.

## Public/private artifact boundary

Git-safe public checkpoint artifacts are limited to explanatory documents,
the three normative machine files, source code and tests, the redacted
`pilot/PILOT_PUBLIC_RECEIPT.json`, and the non-row-level
`pilot/pilot_input_files.json` provenance ledger.

Licensed or row-level pilot evidence remains private on SCC under:

`/project/econdept/qluo/P1_Refraction_WRDS/GATE_RUN_20260905_CONTRACT_V3/pilot`

That private bundle includes:

- `PILOT_PASS.json` or `PILOT_FAIL.json`
- `golden_case_results.json`
- `etf_flag_history_audits.json`
- `pilot_invariants.json`
- `pilot_exposure_observations.csv`
- `pilot_raw_trace_inspection.csv`

The private evidence bundle must remain complete and hash-consistent beside
the canonical private receipt. Licensed rows and their values must not be
copied into Git or repeated in public documentation.

## Fail-closed implementation status

`run_gate0_gate1.py` remains a quarantined pre-contract implementation. Its
preflight must refuse execution before manifest or archive access while
`full_run_enabled` is false. `run_gate0_gate1_scc.sh` must not be submitted,
and Gate 2 must not be launched.

The retained implementation is present only to make scientific-code changes
visible to hashing and review. Replacing it with a contract-conformant full
implementation is a code change and therefore requires a new golden sample
and targeted pilot before any full Gate 0/1 run.

## Local non-data checks

The unit tests and Python compilation checks may be run locally without SCC or
licensed inputs. They do not constitute a pilot or Gate result.
