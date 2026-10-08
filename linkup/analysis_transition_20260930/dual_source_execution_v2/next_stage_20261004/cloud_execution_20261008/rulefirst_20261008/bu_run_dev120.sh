#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:20:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_ruledev
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
LOG="$ROOT/logs/dev120.${JOB_ID}.log"
exec >"$LOG" 2>&1
echo "job_id=$JOB_ID host=$(hostname) slots=${NSLOTS:-unknown} started_utc=$(date -u +%FT%TZ)"
module load python3/3.8.10
python3 "$ROOT/code/prepare_rulefirst_sample.py" --root "$ROOT"
python3 "$ROOT/code/run_rule_batch.py" \
  --input "$ROOT/run/prep/DEV120_SOURCE_PRIVATE.jsonl" \
  --output-dir "$ROOT/run/dev120" --workers "${NSLOTS:-4}" --expected 120 \
  --engine-dir "$ROOT/code/engine" \
  --synthetic-test "$ROOT/code/engine/test_rule_engine_synthetic.py"
echo "completed_utc=$(date -u +%FT%TZ)"
