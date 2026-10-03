# Frozen semantic narrow production handoff

Status at 2026-10-03 16:57 China time: the accepted v2 gate, 2,464 receipt archive,
and exact manifest are present on Huazhong. The final authorized production attempt
has been submitted; operational identifiers are kept in the private trace.

Runtime code:

`/public/home/lilysharp/linkup_analysis_execution_oct02/code/pre_revelio_execution_v1/build_semantic_narrow.py`

The exact manifest is `/public/home/lilysharp/linkup_analysis_execution_oct02/private/full_manifest_v2.jsonl`.
Each row supplies `shard_id`, `shard_dir`, and `receipt`. For each row the batch runner invokes:

```text
source /etc/profile.d/modules.sh
module load anaconda3/2023.09
python build_semantic_narrow.py \
  --shard <manifest shard_dir> \
  --receipt <manifest receipt> \
  --gate /public/home/lilysharp/linkup_analysis_execution_oct02/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json \
  --output <private output>/<shard_id>.parquet
```

The production launcher must use at most eight workers, 8 CPUs, 16 GB, and 12 hours, and must stop submitting at 2026-10-07 18:00 China time. A deterministic first hash prefix is part of production and may be retained. The CLI rejects an absent or non-accepted 2,464-shard gate and rejects receipts that do not bind the selected shard's `SHARD_COMPLETE.json`.

Each shard produces the ad-level Parquet file, a `.durations.parquet` evidence-level private sidecar, and a `.receipt.json`. Do not publish keys or duration rows to Git. Aggregate only after all selected shard receipts pass row conservation and key audits.


## Exact validation runtime archive

The corrected validation module used for the isolated gate is archived beside this document as `runtime_final_receipt_gate.py`. The older cleaning-pipeline snapshot is preserved unchanged. To replay the metadata-only validation with this exact module, set `LINKUP_GATE_ROOT` to the private metadata root and `LINKUP_GATE_MODULE` to the absolute path of this archived module before invoking `build_verified_gate_v2.py`. Do not invoke legacy handoff triggers after the two production submissions recorded in the private operation trace.
