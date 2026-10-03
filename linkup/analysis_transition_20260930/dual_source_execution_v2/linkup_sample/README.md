# LinkUp L1 frozen sample

`build_l1_sample.py` implements section 11.3 of the 2026-10-04 execution attachment using the already-produced T5 join and semantic narrow tables. It does not read original descriptions, rerun semantic extraction, or modify an old result.

The formal frame reproduces the old C1 common support (occupation major × Census region × CREATED year): all A records and, in every cell, `min(N_B, 3*N_A)` B records under seed `20261004`. The private cell table stores `N_A`, `N_B`, both inclusion probabilities, and the frozen old-population weight `W_h`.

The 600-record diagnostic has two disjoint operational frames. The near frame is restricted to the existing T5 technology-candidate join in the 69 old cells and excludes both C1 arms. It is therefore a **candidate-near diagnostic** of C1 arm/role screening, not the contract's broader all-text same-cell frame, and cannot measure technology-term misses outside T5. The broader same-cell coverage is explicitly missing because the usable full-corpus narrow table has no occupation/region columns and would require rebuilding the full Records/O*NET join. The broad frame uses all usable semantic-narrow rows after excluding the entire T5 joined table. This avoids rebuilding the 204.8-million-record occupation join and makes cross-stratum overlap impossible by construction.

Development (200), evaluation (200), and configuration-comparison (80, nested in development) outputs are deliberately named `PROVISIONAL`. They exclude all recoverable prior-review keys, but original text is not present in the L1 inputs, so repeated-description exclusion has not been performed. The private receipt must remain at `keys_complete_subsets_provisional_pending_text_dedup` until selected texts are materialized and cryptographic text-group exclusion is completed. The unavailable historical heldout-400 list is not claimed excluded.

All generated Parquet files and the private receipt contain JOB_HASH/source locators. They belong under `private/`, which is ignored by Git.

After the core checkpoint exists, generate the executable regional materializer inputs without reading raw source files:

```bash
python prepare_dev_text_adapter.py \
  --development /public/home/lilysharp/linkup_analysis_execution_oct02/private/dual_source_execution_v2/linkup_sample/run-JOB_ID/L1_DEVELOPMENT_200_KEYS_PROVISIONAL.parquet \
  --config-compare /public/home/lilysharp/linkup_analysis_execution_oct02/private/dual_source_execution_v2/linkup_sample/run-JOB_ID/L1_CONFIG_COMPARE_80_KEYS_PROVISIONAL.parquet \
  --source-plan /public/home/lilysharp/linkup_analysis_execution_oct02/private/gate_v2_20261003/plans/kunshan.plan.jsonl \
  --source-plan /public/home/lilysharp/linkup_analysis_execution_oct02/private/gate_v2_20261003/plans/wuzhen.plan.jsonl \
  --output-dir /public/home/lilysharp/linkup_analysis_execution_oct02/private/dual_source_execution_v2/linkup_sample/run-JOB_ID/dev_text_adapter
```

The adapter emits `development_200_{region}.selection.json`, `development_200_{region}.source_map.jsonl`, regional 80-key manifests, a private receipt, and `RUN_MATERIALIZE_BY_REGION_PRIVATE.sh`. The generated selections use the exact `selected[].private_key` JSON contract accepted by the frozen `materialize_selected_text.py`. Run the generated commands on their respective regional hosts; the source-map paths are region-local absolute paths.
