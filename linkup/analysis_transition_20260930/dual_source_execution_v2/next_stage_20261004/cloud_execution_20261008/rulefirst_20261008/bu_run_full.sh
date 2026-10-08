#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:20:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_rulefull
set -euo pipefail; umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
exec >"$ROOT/logs/full.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$ROOT/code/run_full_rulefirst.py" \
 --queue "$ROOT/imported/production_standard_20261008/private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl" \
 --represented "$ROOT/imported/production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl" \
 --output-dir "$ROOT/run/full" --engine-dir "$ROOT/code/engine" \
 --synthetic-test "$ROOT/code/engine/test_rule_engine.py" --workers "${NSLOTS:-4}"
