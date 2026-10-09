#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_relover
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
HYBRID="$ROOT/hybrid_production_20261009"
OUT="$HYBRID/run/relation_overlay_v1"
mkdir -p "$ROOT/logs" "$OUT"
exec >"$ROOT/logs/relation_overlay.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$HYBRID/code/run_relation_overlay.py" \
  --dev-baseline "$ROOT/run/dev120/RULE_OUTPUTS_PRIVATE.jsonl" \
  --full-baseline "$ROOT/run/full/FULL7635_RULE_OUTPUTS_PRIVATE.jsonl" \
  --represented "$ROOT/run/full/EXPANDED10000_BINDING_PRIVATE.jsonl" \
  --overlay "$HYBRID/code/relation_overlay.py" \
  --synthetic-test "$HYBRID/code/test_relation_overlay.py" \
  --output-dir "$OUT"
