# Three-shard execution commands

Prepare a private JSONL inventory from published, verified artifacts with
`shard_id`, `region` (`kunshan` or `wuzhen`), absolute `shard_dir`, and absolute
published `receipt`. Include the full frozen-plan inventory; selection is a
fixed hash rank and does not inspect semantic outputs.

After the global gate is accepted:

```bash
python analysis_transition_20260930/execution_oct02_07/pilot_first_wave_3shards.py \
  --inventory /private/path/published_inventory.jsonl \
  --plans /absolute/path/kunshan-plan.jsonl /absolute/path/wuzhen-plan.jsonl \
  --gate /public/home/lilysharp/linkup_release_v1/full_semantic_v1/ALL_REGIONS_VERIFIED_COMPLETE.json \
  --output /private/path/oct02_three_shard_pilot
```

If a diagnostic must run before global acceptance, its receipt must preserve
that status explicitly:

```bash
python analysis_transition_20260930/execution_oct02_07/pilot_first_wave_3shards.py \
  --inventory /private/path/published_inventory.jsonl \
  --plans /absolute/path/kunshan-plan.jsonl /absolute/path/wuzhen-plan.jsonl \
  --pre-gate-diagnostic \
  --output /private/path/oct02_three_shard_pre_gate_diagnostic
```

Neither command submits a cluster job. Do not reuse a pre-gate diagnostic as
the Oct 2 accepted pilot; rerun after the global gate.
