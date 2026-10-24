# Fixed10k empirical delivery, Batch069

This directory contains the reproducible code and public aggregate outputs for the frozen 2026-10-24 SOP. Run `code/wz_run_empirical.sbatch` only on the authorized SCNet environment. The script reads selected metadata columns from the fixed10k parquet and never reads `original_text`.

`results/RUN_RECEIPT_PUBLIC.json` binds the accepted Batch069 ledger, uncertainty register, isolation register, exclusion manifest, fixed frame, code, and every cloud-generated public output by SHA-256. `results/SCHEDULER_RECEIPT_PUBLIC.json` records the successful Slurm job and the retained concrete failure chain. `results/T1_GLOBAL_BASE_COVERAGE_REUSED.csv` is a release-side pointer to the accepted global T4 receipt; it is separate from the job-generated fixed10k tables.

`results/FINAL_RENDER_RECEIPT_PUBLIC.json` binds the separate output-only completion job. Use `T2_EXPERIENCE_CLAUSES_INTERPRETABLE.csv` and the two `*_FINAL.png` figures for review; they add explicit indicator labels and readable core plots without changing any numeric analysis output.

The cloud-private joined analysis table is intentionally absent from Git. Published Formal800 files and global T4 files under `results/` are byte-for-byte copies with separate scope labels.
