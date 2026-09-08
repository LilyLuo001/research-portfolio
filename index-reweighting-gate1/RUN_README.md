# Rule-Based Index Reweighting — Gate 1 Execution

This folder contains a bounded assignment-and-support feasibility audit. It does not estimate headline price-discovery outcomes or claim causal identification.

The raw WRDS mirror is read-only. No proprietary rows, credentials, or licensed source files are committed here. Small metadata summaries and provenance-preserving derived audit tables are committed only when they disclose no proprietary row-level observations.

## Execution environment

- SCC archive: `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902`
- Python module: `python3/3.12.4`
- Run-specific SCC work directory: supplied to `src/run_gate1.sh`; it must be outside the archive.
- Screening window: 2018–2025. Any 2026 evidence is a separately labeled partial extension.

## Required outputs

The root of this folder will contain the decision memo and nine required machine-readable audit tables. `src/` contains executed code and tests; `logs/` records command, retrieval, validation, and access status without secrets.

## Safety

- Never write to the archive.
- Never run whole-project `rsync --delete`.
- Never commit raw or row-level licensed data.
- Never treat filenames, holdings snapshots, or current methodology as exact historical assignment evidence.
- Missing access is reported as `BLOCKED_ACCESS`; it is not recoded as a failed economic design.

Detailed run commands and the final recommendation are added after execution.
