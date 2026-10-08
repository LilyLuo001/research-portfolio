#!/bin/bash
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_ruleprep
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
LOG="$ROOT/logs/prepare.${JOB_ID}.log"
exec >"$LOG" 2>&1
echo "job_id=$JOB_ID host=$(hostname) slots=${NSLOTS:-unknown} started_utc=$(date -u +%FT%TZ)"
module load python3 2>/dev/null || module load python 2>/dev/null || true
python3 "$ROOT/code/prepare_rulefirst_sample.py" --root "$ROOT"
echo "completed_utc=$(date -u +%FT%TZ)"
