# Frozen baseline shared-feature execution

Status: passed on Wuzhen SCNet job `46773912` (`wzhdtest`, exit `0:0`). This is an engineering-equivalence and throughput run on the same lexicographically first shard and the same first 20,000 original-order rows used by the frozen baseline. It did not fit, select, evaluate, or deploy a model and did not write to the frozen model, reference sidecar, or semantic labels.

The Batch001 ledger named in the inference code is read only to reconstruct the training-input identity of the already frozen artifact. It is not the label source for a future training run. Any later fixed final training must explicitly freeze the latest compatible accepted-label snapshot and record its SHA-256 before fitting.

The inference key combines the SHA-256 of the sorted frozen training-context identities with the SHA-256 of the complete pickled fitted `TfidfVectorizer` state. Effective transformer parameters are hashed separately. The 27 frozen targets formed four verified groups of 4, 4, 4, and 15 targets, so the run created four feature matrices and avoided 23 duplicate transforms. This grouping is established from actual training inputs and fitted transformer states rather than inferred from target-family names.

The new sidecar has 20,000 rows and 27 prediction columns. `source_row_0based`, `JOB_HASH`, and all 540,000 prediction cells exactly match the frozen reference: zero mismatches. The new sidecar is byte-identical to the frozen sidecar (`f232c017bf1ff67fec33ca058a9fd2d62da45c3a86f7f788f84ffb22967dc4ee`, 828,756 bytes), despite being written to a new private path.

Measured read-through-atomic-write inference time was 117.922404 seconds, or 169.603055 rows/second. The earlier serial-transform run measured 573.527057 seconds and 34.871938 rows/second on the same prefix, so removing duplicate transforms improved measured end-to-end inference throughput by 4.864 times. The phase times were:

- Parquet read: 0.744168 seconds
- Frozen normalization: 36.673481 seconds
- Four feature transforms: 79.377776 seconds
- Twenty-seven predictions: 0.481771 seconds
- Parquet close and atomic rename: 0.037511 seconds

The full payload through validation, model loading, fitted-state fingerprinting, inference, equivalence comparison, and pre-result-write accounting took 126.713652 seconds (157.836190 rows/second). Scheduler elapsed time was 129 seconds. The process consumed 125.512 user CPU seconds and 1.960 system CPU seconds; scheduler `TotalCPU` was 127.473 seconds. Actual mean CPU use was about one core (0.994 by in-process accounting) despite the eight CPUs requested by the existing partition wrapper. Peak resident memory was 1,230,652 KiB.

The inherited `class_weight="balanced"` setting is unchanged and is not counted as a correction. These remain 27 binary presence predictions. They do not implement year binding, required versus preferred strength, qualification branches and alternatives, evidence spans, or the complete responsibility-subject relation semantics.

Artifacts:

- Frozen model SHA-256: `48dec600da433aa22dd5f9bb4e256af4ce9de92d5e81d2a0e46c71602dba1e4d`
- Frozen and optimized sidecar SHA-256: `f232c017bf1ff67fec33ca058a9fd2d62da45c3a86f7f788f84ffb22967dc4ee`
- Optimized inference code SHA-256: `715ff32baf169fe3fe9d4b06cad9a9a5883d62a04a09d1df2c10d1f1289b8bf9`
- Batch wrapper SHA-256: `5c9cc841d45642248d56935364f8ade8a01d198f636dd6211a73999a3338fe70`
- Public result SHA-256: `713f7d418c52379f344011fd96938162c85b87e2b17fcbecbfadf5b5ecd6a148`
- Standard output SHA-256: `1d47ad5040652f30e8080705d1399b3b0628563f0216e5f136e322c87f7665a6`
- Empty standard error SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The detailed receipt, including all group and fitted-state fingerprints, is `results/SHARED_FEATURE_RESULT_PUBLIC.json`. The optimized sidecar remains private at `/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/sidecar/first_linkup_shard_first20000_predictions_shared_features.parquet`.
