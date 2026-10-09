#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_final6
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
FINAL="$ROOT/final_tables_20261009"
OUT="$FINAL/run/final_tables_v2"
mkdir -p "$ROOT/logs" "$OUT"
exec >"$ROOT/logs/final_tables.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$FINAL/code/build_final_tables.py" \
  --baseline "$ROOT/run/full/FULL7635_RULE_OUTPUTS_PRIVATE.jsonl" \
  --overlay "$ROOT/hybrid_production_20261009/run/relation_overlay_v1/FULL7635_RELATION_OVERLAY_PRIVATE.jsonl" \
  --represented "$ROOT/run/full/EXPANDED10000_BINDING_PRIVATE.jsonl" \
  --contract "$FINAL/control/MEASUREMENT_RELEASE_CONTRACT.json" \
  --output-dir "$OUT"
