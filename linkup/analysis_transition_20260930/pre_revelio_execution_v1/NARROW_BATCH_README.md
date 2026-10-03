# Semantic narrow batch runner

Status at 2026-10-03 16:57 China time: code ready and the final authorized production attempt is submitted against the accepted v2 gate and exact 2,464-row manifest. Scheduler identifiers remain in the private operation trace.

`run_semantic_narrow_batch.py` validates the accepted global gate, exact union of 2,464 frozen plan IDs, every manifest row's published receipt and `SHARD_COMPLETE.json`, and a work-directory identity binding over the builder, gate, manifest, and plans. It runs at most eight subprocesses, pins each subprocess to one numerical-library thread, and passes `--threads 1` to the narrow builder.

A shard is skipped only when its ad Parquet, duration Parquet, builder receipt, and batch identity marker all exist; both Parquet hashes and row counts must match the receipt, and the marker must match the current shard ID, source receipt hash, completion hash, runner hash, builder hash, gate hash, manifest hash, and plan-set hash. Any failed or stale shard is rebuilt. An advisory lock covers the whole work-directory run. Aggregation starts only after all 2,464 shards pass the same validation, publishes through an atomic temporary directory, and is reused after a crash only when its hashes and complete identity-bound receipt verify.

The additive aggregate writes `T2_EXPERIENCE_AD_RATES.csv` with all usable canonical ads as the explicit denominator, including ads with no detected experience, and `T2_DURATION_BOUND_DISTRIBUTION.csv` at the evidence level. Duration sidecars include only evidence from usable ads, so the scope matches the rate denominator. An available object with no duration evidence receives an explicit zero-evidence row. The aggregation never collapses clauses to an ad-level minimum. `exact_or_unspecified` is separated from interpretable lower-bound bins. `occupation_task` is emitted as unmeasured/NA under D10, never zero.

The empty-shard writer uses a fixed schema, so a legitimate zero-ad shard retains all columns; measurable flags are Boolean and `exp_occupation_task_main` is a nullable Boolean containing no values, with availability false.

Focused validation:

```sh
python test_run_semantic_narrow_batch.py
```

The fixture forces one shard to fail once, verifies restart resumes the completed shard and rebuilds only the failed shard, checks identity-change refusal, checks zero-ad schema preservation, and checks occupation/task remains unavailable.

The production invocation is fixed in `run_semantic_narrow_hz.sbatch`. It consumes
`private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json`, the two plans under
`private/gate_v2_20261003/plans/`, and `private/full_manifest_v2.jsonl`. The guarded
launcher is `trigger_semantic_narrow_once.sh`; it requires all three inputs, an exact
2,464-line manifest, and the 2026-10-07 18:00 China-time cutoff before submitting.
The batch shell explicitly initializes `/etc/profile.d/modules.sh` before loading the
verified `anaconda3/2023.09` runtime.
