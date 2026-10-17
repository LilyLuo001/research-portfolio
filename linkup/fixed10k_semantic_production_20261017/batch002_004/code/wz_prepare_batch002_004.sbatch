#!/bin/bash
#SBATCH --job-name=f10k_b002_004_prep
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/receipts/slurm-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/receipts/slurm-%j.err

set -eo pipefail
set +u
source /etc/profile
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077

T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
F=/work/home/lilysharp/private/formal800_20261012
PRIOR="$T/private/batch001/final"
mkdir -p "$T/private/batch002_004" "$T/public" "$T/receipts"

python3 "$T/code/prepare_batch002_004.py" \
  --queue "$PRIOR/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --ledger "$PRIOR/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --uncertainty "$PRIOR/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --prior-receipt "$T/receipts/BATCH001_FINALIZE_RECEIPT.json" \
  --frame /work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet \
  --normalizer "$F/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py" \
  --formal-schema "$F/code/FORMAL800_REVIEW_SCHEMA.json" \
  --formal-instructions "$T/code/REVIEW_INSTRUCTIONS.md" \
  --formal-validator "$F/code/validate_reviews.py" \
  --private-output "$T/private/batch002_004" \
  --public-receipt "$T/public/BATCH002_004_PREP_RECEIPT.json" \
  --repository-commit 4ca089a5dc92980aba8f89b7ddb0e54a9d0aa5d6
