#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:20:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_context
set -euo pipefail; umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
OUT="$ROOT/run/contextual_handoff_20261008"
exec >"$ROOT/logs/contextual_handoff.${JOB_ID}.log" 2>&1
module load python3/3.8.10
test ! -e "$OUT"; mkdir -m 700 "$OUT"
python3 "$ROOT/code/build_contextual_handoff.py" \
 --queue "$ROOT/imported/production_standard_20261008/private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl" \
 --represented "$ROOT/imported/production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl" \
 --full-results "$ROOT/run/full/FULL7635_RULE_OUTPUTS_PRIVATE.jsonl" \
 --engine-dir "$ROOT/code/engine" --output-dir "$OUT" \
 --budget-contract "$ROOT/contextual_contract/budget_contract.json" \
 --pricing "$ROOT/contextual_contract/pricing.json" \
 --variable-contract "$ROOT/contextual_contract/ROOT_VARIABLE_CONTRACT.json"
