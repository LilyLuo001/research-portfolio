#!/bin/bash
#SBATCH --job-name=prod_coverage_20261017
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/production_coverage_20261017/receipts/slurm-%j.out
#SBATCH --error=/work/home/lilysharp/private/production_coverage_20261017/receipts/slurm-%j.err

set -eo pipefail
set +u
source /etc/profile
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077

T=/work/home/lilysharp/private/production_coverage_20261017
F=/work/home/lilysharp/private/formal800_20261012
C=/work/home/lilysharp/linkup_cloud_execution_20261008/run-20261008T053138Z/payload
mkdir -p "$T/private" "$T/public" "$T/receipts"

python3 "$T/code/reconcile_coverage.py" \
  --frame /work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet \
  --normalizer "$F/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py" \
  --normalizer-sha256 336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd \
  --formal-reviews "$F/private/validation/final/validated_reviews.jsonl" \
  --formal-packet "$F/private/validation/final/FINAL_BOUND_PACKET_PRIVATE.jsonl" \
  --formal-linkage "$F/private/freeze/HIDDEN_LINKAGE_PRIVATE.jsonl" \
  --wave01-packet "$T/input/wave01/DEV24_RELATION_DECISIONS_PRIVATE.jsonl" \
  --wave01-overlay "$T/input/wave01/PRO_SEMANTIC_REVIEW_OVERLAY_PRIVATE.jsonl" \
  --wave02-packet "$T/input/wave02/WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl" \
  --wave02-overlay "$T/input/wave02/WAVE02_REVIEW_OVERLAY_PRIVATE.jsonl" \
  --batch001 "$C/production_standard_20261008/private/batch001/FINAL_CANDIDATES_PRIVATE.jsonl" \
  --batch002 "$C/batch002_execution/private/batch002/FINAL_CANDIDATES_PRIVATE.jsonl" \
  --exclusion-hashes "$F/private/exclusions/EXCLUSION_HASHES_ONLY_PRIVATE.jsonl" \
  --private-ledger "$T/private/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --private-queue "$T/private/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --private-uncertainty "$T/private/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --public-coverage "$T/public/COVERAGE_AGGREGATES_PUBLIC.json" \
  --receipt "$T/receipts/ANALYSIS_RECEIPT.json"
