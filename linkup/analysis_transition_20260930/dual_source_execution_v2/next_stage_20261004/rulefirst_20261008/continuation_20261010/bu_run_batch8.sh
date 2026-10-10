#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=02:00:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -t 1-8
#$ -tc 4
#$ -N lk_prod8
#$ -hold_jid 8004843
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010
mkdir -p "$ROOT/logs" "$ROOT/output"
exec >"$ROOT/logs/production_batch8.${JOB_ID}.${SGE_TASK_ID}.log" 2>&1
module load python3/3.8.10
PYTHONPATH=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code:${PYTHONPATH:-} \
python3 "$ROOT/code/run_manifest_entry.py" \
  --manifest "$ROOT/control/private/BATCH_0002_MANIFEST_PRIVATE.json" \
  --index "${SGE_TASK_ID}" --stage-root "$ROOT/staging" --output-root "$ROOT/output" \
  --runner /projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code/run_one_shard.py \
  --workers "${NSLOTS:-4}"
