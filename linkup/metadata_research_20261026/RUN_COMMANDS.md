# Fixed10k metadata and descriptive comparison

Execution date: 2026-10-26. Run only on the authorized Kunshan SCNet environment with its existing Python 3.8.10 / stage_b runtime. This release installs nothing and invokes no model.

## Recorded execution

- Footer/dependency probe: `125613326`, completed in 22 seconds.
- Main linkage/comparison: `125615039`, 8 CPU / 16 GB, `kshctest02`, 30-minute limit.
- Independent output verification: `125615844`, 2 CPU / 4 GB, dependent on successful main completion.
- Frozen pre-result implementation/specification: Git `634a6b2`.

The first 4 CPU / 16 GB submission was rejected before allocation because the partition's memory-to-CPU rule was exceeded. No job or research output was created by that attempt. The accepted 8 CPU request changes execution resources only.

## Commands actually submitted

```sh
sbatch /public/home/lilysharp/linkup_metadata_research_20261026/code/ks_run_metadata.sbatch
sbatch --dependency=afterok:125615039 /public/home/lilysharp/linkup_metadata_research_20261026/code/ks_verify.sbatch
```

Do not resubmit completed research work. The main wrapper retains a completed-receipt guard and reuses a completed metadata append when resuming a concrete comparison execution failure.

## Retained private outputs

Under `/public/home/lilysharp/linkup_metadata_research_20261026/run001/`:

- `private/AD_LEVEL_RESEARCH_PRIVATE.parquet`: original 10,000 advertisements and all original columns unchanged, with metadata/provenance appended.
- `comparison_private/CELL_SUPPORT_RESULTS_WEIGHTS_PRIVATE.csv`: private vendor-company / SOC-major counts, rates and aggregation weights.

These files stay on SCNet; no advertisement key, company identity, raw title or reference row is released to Git.

## Public outputs and verification

The cloud `public/` and `comparison_public/` directories contain aggregate coverage, scope/schema, support, descriptive results, sparsity distributions and receipts. Sanitized copies are retained in this release's `results/` directory.

`verify_outputs.py` independently checks exact original Arrow columns/order/values, source/output hashes, observed support membership, per-cell denominators, fixed weights, recorded-unknown bounds and mandatory-major missingness. It does not certify reference semantics, human accuracy, market representativeness, identical jobs within a SOC major, or causal interpretation.

The comparison specification fixes unit ad weights, observed sample support, four SOC majors weighted 0.25 each, and no renormalization if any mandatory major is unavailable. Unknown bounds cover only recorded outcome unknowns within retained cells. No inference is made about the date of the current description from Records observation dates.
