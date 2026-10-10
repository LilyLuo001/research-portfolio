#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:30:00
#$ -l mem_per_core=8G
#$ -l no_gpu=TRUE
#$ -N lk_meta_keys
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010/metadata_join
mkdir -p "$ROOT/logs" "$ROOT/output" "$ROOT/private/keys"
exec >"$ROOT/logs/prepare_first5.${JOB_ID}.log" 2>&1
module load python3/3.8.10
python3 "$ROOT/code/test_targeted_metadata_join.py"
python3 "$ROOT/code/targeted_metadata_join.py" prepare-keys \
  --postings-manifest "$ROOT/control/FIRST5_POSTINGS_MANIFEST_PRIVATE.json" \
  --key-dir "$ROOT/private/keys" \
  --public-receipt "$ROOT/output/FIRST5_KEY_PREP_RECEIPT_PUBLIC.json" \
  --expected-rows 424226
