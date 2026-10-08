#!/bin/bash
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:03:00
#$ -l mem_per_core=1G
#$ -l no_gpu=TRUE
#$ -N lk_ruleschema
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
exec >"$ROOT/logs/schema.${JOB_ID}.log" 2>&1
module load python3 2>/dev/null || module load python 2>/dev/null || true
python3 "$ROOT/code/inspect_represented_schema.py"
