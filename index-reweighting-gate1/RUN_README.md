# Rule-Based Index Reweighting — Gate 1 Execution

This folder is an executed, bounded assignment-and-support feasibility audit. It asks whether repeated rule-based index reweightings have observable assignments, a credible prospective comparison, and usable intersections with FOMC common-news dates. It does not estimate headline price-discovery outcomes, claim causal identification, or report statistical power.

The raw WRDS mirror was treated as read-only. No proprietary rows, credentials, workbook, or licensed source file is committed. The public artifacts contain aggregate audit metadata and source-linked derived tables only.

## Controlling inputs and scope

- Governing execution prompt: `index_reweighting_gate1_execution_prompt.txt`, SHA-256 `a2d81c35f614c21bf38ee8a41dd40c470755b90a0f96b7306679b3564b9f56e0`.
- Archive guide: `P1_Refraction_WRDS_Data_Usage_Manual_UPDATED_20260903.md`, SHA-256 `bc13934789517677f87371e3d8673e462a8d535cfae4913aa06ed7d7c1feb5d8`.
- Screening window: 2018–2025. Rows for 2026 are explicitly marked as a partial extension.
- SCC archive: the canonical path supplied in the governing execution prompt, passed explicitly with `--archive` and omitted from public execution logs.
- SCC run directory: a permission-controlled directory outside the archive; its account-specific locator is omitted from the public package.
- SCC Python module used for Stage A: `python3/3.12.4`.

The exact input lineage is in `docs/INPUT_LINEAGE.md`. The current machine-generated counts and scope guardrail are in `logs/gate1_summary.json`; that file controls if prose and an intermediate log ever disagree.

## Reproduction

Stage A is the only licensed-data step. It was executed on BU SCC against the canonical mirror; public-safe commands, aggregate results, public-artifact hashes, and test results are recorded in `logs/stage_a_commands.log`, `logs/stage_a_evidence.json`, and `logs/stage_a_validation.log`. Licensed-source paths, identifiers, and hashes are retained only in the permission-restricted SCC lineage bundle. The code is `src/audit_archive.py`, and its tests can be run locally without the archive:

```bash
python3 -m pytest -q tests/test_audit_archive.py
```

The public-source and analytical builders are deterministic. Download the public SF Fed USMPD workbook from the URL registered in `logs/stage_e_usmpd_registry.csv` to a temporary local path, then run:

```bash
./src/run_gate1.sh /temporary/path/USMPD.xlsx
```

The script rebuilds the rule/source registry, event ledger, incomplete-dose audit, FOMC calendar and intersections, comparison/gap audits, and summary; it then runs the full tests and package validator. The workbook is used only for metadata/schema screening, is not copied into the repository, and should be deleted from the temporary path after the run.

Equivalent explicit commands are:

```bash
python3 src/build_rule_registry.py
python3 src/build_fomc_calendar.py --usmpd-xlsx /temporary/path/USMPD.xlsx
python3 src/build_design_audit.py
python3 src/summarize_gate1.py
python3 -m pytest -q
python3 src/validate_gate1.py
```

## Output map

- `local_data_catalog.csv` — aggregate physical archive inventory and target-membership search status.
- `fund_identifier_and_coverage_audit.csv` — fund-year holdings and daily-data screening coverage.
- `source_and_rule_registry.csv` — primary sources and historically bounded rule regimes.
- `rebalance_event_ledger.csv` — potential events, dependence groups, timing, and binding classifications.
- `assignment_doses_and_evidence.csv` — available numerical assignment evidence with A/B/C/U grading.
- `fomc_calendar.csv` — official meeting/statement calendar, exceptions, and scope labels.
- `assignment_and_fomc_support.csv` — event-stage/FOMC intersections and overlap diagnostics.
- `comparison_and_interference_audit.csv` — prospective causal-design threats and deliberately gated diagnostics.
- `remaining_input_gaps.csv` — exact unresolved inputs, blocker flags, and next actions.
- `FINAL_DECISION.md` — the decision memo and minimum next retrieval/design gate.
- `docs/OPUS_5_HIGH_REVIEW_PACKAGE.md` — self-contained package for manual independent review.

## Evidence and safety rules

- Never write to the archive or run a whole-project `rsync --delete`.
- Never commit raw or row-level licensed data, credentials, or temporary public workbooks.
- Do not treat an index-return series, industry-membership table, ETF holdings snapshot, or current methodology as historical constituent assignments.
- Do not infer nonbinding status from missing evidence, exact doses from selected rounded rows, or trader-time availability from a later publication.
- Rule-source grade, event-classification grade, and assignment-observability grade are different dimensions.
- Daily MIDAS and daily CRSP fields are not intraday quotes/trades or an empirical latency path.
- A shared policy date, issuer, or FOMC meeting is not a new independent shock for every table row.
- Access failure is an input gap, not evidence that the economic mechanism is false.

See `docs/EVIDENCE_CONTRACT.md` for the complete interpretation contract and `logs/final_validation_20260908.log` for the final integrity checks.

The technical redaction policy is not a legal opinion. Whether the remaining aggregate fund-year statistics may be redistributed publicly is a maintained compliance assumption that requires confirmation under the researcher's institutional and vendor-license policies.
