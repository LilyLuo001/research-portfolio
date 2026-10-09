#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:20:00
#$ -l mem_per_core=4G
#$ -l no_gpu=TRUE
#$ -hold_jid 7979088,7979089,7979111,7979090
#$ -N lk_full5qa
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009
exec >"$ROOT/logs/verify_shard_set_5.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$ROOT/code/verify_shard_set_outputs.py" \
  --manifest "$ROOT/code/SHARD_SET_5_MANIFEST_PUBLIC.json" \
  --verifier "$ROOT/code/verify_one_shard_outputs.py" \
  --allowed-root /projectnb/econdept/qluo/linkup_rulefirst_20261008 \
  --output "$ROOT/output/SHARD_SET_5_QA_PUBLIC.json"
