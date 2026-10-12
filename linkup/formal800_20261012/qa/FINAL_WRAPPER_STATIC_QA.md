# Final wrapper static QA

Date: 2026-10-12  
Reviewer: `/root/formal800_repair_i` (`gpt-5.6-sol`, medium)  
Scope: static inspection only of `code/wz_finish_formal800.sbatch` and `code/run_review_validation.py` against the argument contracts of `code/merge_formal800_audit.py` and `code/analyze_formal800.py`. No pipeline, validation, synthetic-data, real-data, statistics, cloud, or Git command was run.

## Resolved deployment prerequisite

`code/wz_finish_formal800.sbatch:27` sets `SCHEMA=$C/FORMAL800_REVIEW_SCHEMA.json`, where `C=$W/code`. The repository checkout does not contain that deployment-only copy, so the initial static inspection flagged the path for verification. The scheduled remote workspace was subsequently inspected and contains `/work/home/lilysharp/private/formal800_20261012/code/FORMAL800_REVIEW_SCHEMA.json` (11,586 bytes), SHA-256 `fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e`, matching the schema used by successful jobs.

The deployed schema prerequisite is therefore satisfied and no code-path change is needed. Core code was not edited during this QA.

## Other static findings

No material CLI-orchestration blocker was found in the inspected scope.

- Both `run_review_validation.py` invocations supply all five required arguments. The orchestrator builds combined packet/review inputs, delegates to `validate_reviews.py`, requires a passing receipt, retains the bound packet, and writes an orchestration receipt.
- The shared merge arguments exactly match the required merge CLI. The `finalize` call supplies the optional root-resolution file together with its required receipt, and the merge emits the `FINAL_REVIEW_RAW_PRIVATE.jsonl` consumed by the final validator.
- The final analysis call supplies all four required analysis arguments. It analyzes the already finalized and revalidated review set, so omitting the optional resolved-overlay pair is consistent with the analysis CLI.
- The wrapper fails closed on nonzero subprocess exits through `set -e`, constrains root adjudication to 1–40 rows, checks the frozen 719-row primary bound packet before final validation, and requests exactly 719 final records.

Static path prerequisites such as the consolidated assignment manifests and frozen private inputs must exist in the scheduled workspace; their contents and runtime production were outside this CLI-only review.
