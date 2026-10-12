#!/bin/bash
# Submit only after static QA and an authenticated SCNet preflight confirm the
# cache and every explicit exclusion manifest path.  This file is unsubmitted.
#SBATCH --job-name=formal800-freeze
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/freeze-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/freeze-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/work/home/lilysharp/private/formal800_20261012
FIXED=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet
RULE=$ROOT/code/frozen_rulefirst_v1_2
EXCLUSION=$ROOT/private/exclusions/EXCLUSION_HASHES_ONLY_PRIVATE.jsonl
for p in "$FIXED" "$EXCLUSION" "$RULE/rule_engine.py" "$RULE/legacy_v5_frozen.py"; do test -f "$p"; done
umask 077
python3 "$ROOT/code/freeze_formal800_sample.py" --frame "$FIXED" --frozen-rule-dir "$RULE" \
 --exclusion "$EXCLUSION" \
 --arm-map-json '{"A":"A","B":"B","C":"C"}' --private-output "$ROOT/private/freeze" \
 --public-receipt "$ROOT/public/FORMAL800_FREEZE_RECEIPT_PUBLIC.json"
