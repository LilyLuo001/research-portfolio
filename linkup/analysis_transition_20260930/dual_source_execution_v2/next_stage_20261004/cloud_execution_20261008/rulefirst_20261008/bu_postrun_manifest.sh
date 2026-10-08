#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:05:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_rulepost
set -euo pipefail; umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
exec >"$ROOT/logs/postrun.${JOB_ID}.log" 2>&1
module load python3/3.8.10
test -f "$ROOT/run/full/FULL_RUN_RECEIPT_PUBLIC.json"
test -f "$ROOT/run/eval80/RUN_RECEIPT_PUBLIC.json"
python3 "$ROOT/code/summarize_and_manifest.py"
