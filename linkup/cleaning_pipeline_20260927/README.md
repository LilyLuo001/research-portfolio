# LinkUp Job-Ad Cleaning Pipeline — reproducibility snapshot

This directory is the content-addressed Git methods snapshot for the LinkUp
job-ad cleaning work as of 2026-09-27. It records how raw job-ad files were
checked, sampled, parsed, normalized, evaluated, and reduced to aggregate
research measures. Historical implementation directories (`stage_c`,
`stage_c_v2` through `stage_c_v5`) are preserved as versioned artifacts inside
one current snapshot; they are not presented as separate Git history.

## Pipeline architecture

1. **Input and integrity checks.** Stage B plans define file-level integrity,
   time-field, deduplication, and cross-region comparison requirements.
2. **Text extraction and sampling.** `stage_c` provides deterministic sample
   preparation and requirement-candidate extraction.
3. **Support and temporal audits.** `stage_c_v2` checks occupation-support
   joins and remote-work timing.
4. **Parser revisions and evaluation.** `stage_c_v3`, `stage_c_v4`, and
   `stage_c_v5` record successive parser rules, release gates, portability
   checks, and aggregate validation. Human annotation was unavailable for this
   snapshot; model review is diagnostic and must not be described as human
   validation.
5. **Bounded execution.** `stage_c_batch_v1` records the memory-bounded batch
   runner and per-file receipts.
6. **Compact candidate artifacts.** `stage_c_compact_v1` records the measured
   16,000-row cluster run and its documented limitations. The active
   `stage_c_compact_v2` correction is supported by a 2,926-row local round-trip
   check and has not been run on the cluster.
7. **Evaluation-frame preparation.** `stage_c_evaluation_v2` defines the
   regional 1,000-ad annotation frame. It combines an 800-record probability
   core with a 200-record diagnostic supplement across 32 selected shards. The
   Git snapshot contains aggregate coverage/grouping reports only; it makes no
   national or full-corpus prevalence claim. A completed calibration-only model
   diagnostic uses 32 primary references and an independent 8-record subset;
   it is not human validation and does not establish semantic release.
8. **Aggregate baseline.** `stage_d_baseline_v1` constructs occupation-by-time
   summaries from cleaned inputs.

The current measurement contract is under
`source_snapshot/research_contract_v1/`. It governs variable release and the
separation between descriptive, exploratory, and validated claims.

## Reproducing the code snapshot

From the repository root, point the exporter at an authorized private working
tree containing the paths in `source_manifest.txt`:

```bash
python3 linkup/cleaning_pipeline_20260927/tools/export_snapshot.py \
  --source-root /path/to/LinkUp_Research_20260924
python3 linkup/cleaning_pipeline_20260927/tools/scan_release.py
```

The exporter copies only the explicit allowlist and writes source/snapshot
SHA-256, file size, and snapshot time to `BUILD_MANIFEST.json` and
`provenance.json`. A successful release scan produces no output. Findings
contain rule labels and filenames only.

The scripts that run analysis still require the private raw data layout and the
software packages listed in `requirements.txt`. The private source archive did
not contain a frozen package lock, so the package list must not be read as an
exact historical environment. Paths in cluster submission files must be adapted
to the authorized compute environment. Aggregate reports in this snapshot
document completed runs; they do not make the licensed data publicly
reproducible.

## Data-access boundary

This Git snapshot excludes licensed raw advertisements, advertisement samples,
private blind-review packets, individual text snippets, private metadata,
Parquet and Arrow datasets, archives, full source manifests, raw scheduler
logs, server-login configuration, credentials, and access URLs. Tests known to
contain production-derived job hashes or advertisement-like prose are also
excluded. Running the omitted integration tests requires authorized private
fixtures; their absence does not change the published parser code or aggregate
receipts.

The evaluation archive also excludes sample/source-selection manifests,
calibration and sealed-test records, annotation rows, model-diagnostic mappings,
and exclusion lists containing record identifiers. Only aggregate frame counts,
coverage, grouping checks, and completion hashes are retained.

The permitted outputs are code, contracts, plans, aggregate reports, validation
summaries, and bounded execution receipts. They support a detailed paper-methods
description while respecting source-data licensing and privacy constraints.

## Version interpretation

See `CHANGELOG.md` for factual differences represented by the snapshot. This is
a single current export. Directory names document implementation versions; they
must not be interpreted as reconstructed commit dates.
