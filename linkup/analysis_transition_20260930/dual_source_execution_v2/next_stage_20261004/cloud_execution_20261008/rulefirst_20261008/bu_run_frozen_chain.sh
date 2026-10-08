#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=00:30:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_rulefreeze
set -euo pipefail; umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008
exec >"$ROOT/logs/frozen_chain.${JOB_ID}.log" 2>&1
module load python3/3.8.10
test -f "$ROOT/run/dev120/RUN_RECEIPT_PUBLIC.json"
test ! -e "$ROOT/run/dev120_v1.1"
mv "$ROOT/run/dev120" "$ROOT/run/dev120_v1.1"
python3 "$ROOT/code/run_rule_batch.py" --input "$ROOT/run/prep/DEV120_SOURCE_PRIVATE.jsonl" \
 --output-dir "$ROOT/run/dev120" --workers "${NSLOTS:-4}" --expected 120 \
 --engine-dir "$ROOT/code/engine" --synthetic-test "$ROOT/code/engine/test_rule_engine.py"
python3 "$ROOT/code/run_full_rulefirst.py" \
 --queue "$ROOT/imported/production_standard_20261008/private/full_queue/UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl" \
 --represented "$ROOT/imported/production_standard_20261008/private/full_queue/REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl" \
 --output-dir "$ROOT/run/full" --engine-dir "$ROOT/code/engine" \
 --synthetic-test "$ROOT/code/engine/test_rule_engine.py" --workers "${NSLOTS:-4}"
python3 "$ROOT/code/run_rule_batch.py" --input "$ROOT/run/prep/EVAL80_SOURCE_PRIVATE.jsonl" \
 --output-dir "$ROOT/run/eval80" --workers "${NSLOTS:-4}" --expected 80 \
 --engine-dir "$ROOT/code/engine" --synthetic-test "$ROOT/code/engine/test_rule_engine.py"
python3 "$ROOT/code/make_eval6_packet.py" --source "$ROOT/run/prep/EVAL80_SOURCE_PRIVATE.jsonl" \
 --results "$ROOT/run/eval80/RULE_OUTPUTS_PRIVATE.jsonl" --output "$ROOT/run/eval80/EVAL6_FULLTEXT_EVIDENCE_PRIVATE.jsonl"
echo "completed_utc=$(date -u +%FT%TZ)"
