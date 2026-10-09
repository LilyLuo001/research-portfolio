#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:10:00
#$ -l mem_per_core=4G
#$ -l no_gpu=TRUE
#$ -N lk_full1qa
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009
exec >"$ROOT/logs/verify_one_shard.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$ROOT/code/verify_one_shard_outputs.py" \
  --posting "$ROOT/output/shard_b605d84d410013b1/POSTING_NARROW_PRIVATE.parquet" \
  --evidence "$ROOT/output/shard_b605d84d410013b1/EVIDENCE_PRIVATE.parquet" \
  --production-receipt "$ROOT/output/SHARD_b605d84d410013b1_RECEIPT_PUBLIC.json" \
  --expected-runner-sha256 3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44 \
  --output "$ROOT/output/SHARD_b605d84d410013b1_QA_PUBLIC.json"
