# D64 bounded engineering repair

This directory versions the D64 engineering repair without changing D63 code, accepted outputs, or frozen extraction rules. The cloud deployment root is:

`/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010`

The controller keeps `TARGET_LAST=5`. It requires the pinned measurement-use contract SHA `62d56fbef87ecf0afd8479fee95101668aec0ffed23ea39cacc0ac39e966526f` and records `measurement_use=evidence_bearing_candidates_not_validated_requirements` in each new private manifest and public prep receipt.

Repairs:

- All wrappers disable nounset while sourcing the cluster profile and loading Python, then restore nounset.
- The controller takes an exclusive directory claim. It persists `submitting_*` before each `sbatch` call and persists each returned job ID immediately. A missing/uncertain response stops for manual inspection; it is never automatically resubmitted. Completed next-wave submissions are idempotent no-ops.
- Production checks free space before every shard lane starts a shard. Admission requires the 10 GB reserve plus a conservative 1 GB per-shard allowance. This is explicitly an admission check, not a hard quota.
- Rolling QA fails if the sixteen new shard outputs exceed 4,000,000,000 bytes.
- First-five public QA requires exact unique key sets: 4 technology rows, 132 raw outcome rows, 44 occupation-standardized rows, 22 company-occupation rows, and 48 entry/responsibility rows. It checks published bounds and deltas and explicitly does not claim an independent recomputation of common-support cells, weights, stratified rates, or semantics.

Static validation performed locally: `bash -n` passed for all four wrappers, and all three Python files compiled in memory. No raw data or analysis was run locally.

Expected code SHA-256 values:

```text
a7d2eadc009673f46228708216f615831d8bd64606f71795f882a371fdb4b1a0  rolling/code/wz_rolling_controller.py
059df18d4a3a9a4c88b0990e613bb9e5db0e2fccc00d3c070bb67ff76b6c3661  rolling/code/wz_rolling_controller.sbatch
6a37c259bb3c226f50a35e520fbbcbd1173ace4cd4dd1463fb36faa7e95bf686  rolling/code/wz_rolling_production.sbatch
b8ae211510f0eb6d24792aee2cca8c6aa07f4c12a9cf07b2280fa7bdd8d1dd8d  rolling/code/wz_rolling_qa.py
3fd1b0d5ed1273ff81ff0607a4c080985352410163b7f72596c95ac28ee738f8  rolling/code/wz_rolling_qa.sbatch
1dd5e61220be3ac26b2b609f2439ba05d4dd47e113ca6e59a3de2db898641bcb  first5_analysis/code/qa_first5_comparison.py
39c2c7f20f472ee5f039c11e606ec331f4a333f06c7542394c86f13f80c4c358  first5_analysis/code/wz_qa_first5_comparison.sbatch
```

Deployment must create `rolling/{logs,private,public}` and `first5_analysis/{logs,public}` below the cloud deployment root before submission. Keep the old controller unable to launch. After wave 2 QA passes, start the D64 controller with `CURRENT_WAVE=2`; if submitted before that QA completes, attach an `afterok` dependency to the wave 2 QA job. Run the D64 first-five QA wrapper separately. Only the designated cloud-check worker deploys or commits this patch.
