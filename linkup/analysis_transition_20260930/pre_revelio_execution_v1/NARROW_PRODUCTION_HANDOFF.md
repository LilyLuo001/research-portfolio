# Frozen semantic narrow production handoff

Status at 2026-10-03 15:54 China time: code and fixture are staged on Huazhong, but production has not been submitted because the accepted global publication gate and the 2,464 receipt archive are not yet present there.

Runtime code:

`/public/home/lilysharp/linkup_analysis_execution_oct02/code/pre_revelio_execution_v1/build_semantic_narrow.py`

Use the existing private full manifest only after the unchanged first-wave trigger has observed both the accepted gate and exactly 2,464 published receipt wrappers. Each manifest row already supplies `shard_id`, `shard_dir`, and `receipt`. For each row invoke:

```text
module load anaconda3/2023.09
python build_semantic_narrow.py \
  --shard <manifest shard_dir> \
  --receipt <manifest receipt> \
  --gate /public/home/lilysharp/linkup_release_v1/full_semantic_v1/ALL_REGIONS_VERIFIED_COMPLETE.json \
  --output <private output>/<shard_id>.parquet
```

The production launcher must use at most eight workers, 8 CPUs, 16 GB, and 12 hours, and must stop submitting at 2026-10-07 18:00 China time. A deterministic first hash prefix is part of production and may be retained. The CLI rejects an absent or non-accepted 2,464-shard gate and rejects receipts that do not bind the selected shard's `SHARD_COMPLETE.json`.

Each shard produces the ad-level Parquet file, a `.durations.parquet` evidence-level private sidecar, and a `.receipt.json`. Do not publish keys or duration rows to Git. Aggregate only after all selected shard receipts pass row conservation and key audits.
