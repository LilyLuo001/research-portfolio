#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_dev24
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
HYBRID="$ROOT/hybrid_production_20261009"
OUT="$HYBRID/run/dev24_relation_decisions"
mkdir -p "$ROOT/logs" "$OUT"
exec >"$ROOT/logs/dev24_relation_decisions.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$HYBRID/code/select_dev24_decisions.py" \
  --source "$ROOT/run/prep/DEV120_SOURCE_PRIVATE.jsonl" \
  --rule-output "$ROOT/run/dev120/RULE_OUTPUTS_PRIVATE.jsonl" \
  --output-dir "$OUT" \
  --per-group 4
