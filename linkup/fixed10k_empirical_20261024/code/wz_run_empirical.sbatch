#!/bin/bash
#SBATCH --job-name=fixed10k_empirical
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:40:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/logs/%x-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/logs/%x-%j.err
set -eo pipefail
source /etc/profile
set -u
module load apps/anaconda3/2023.09
ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024
test ! -e "$ROOT/public/RUN_RECEIPT_PUBLIC.json" || { echo "guard: already complete"; exit 0; }
python "$ROOT/code/run_empirical.py" \
 --ledger /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/prepared/batch069/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl \
 --fixed /work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet \
 --exclusions /work/home/lilysharp/private/formal800_20261012/private/exclusions/EXCLUSION_HASHES_ONLY_PRIVATE.jsonl \
 --uncertainty /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/prepared/batch069/final/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl \
 --final-receipt /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/receipts/BATCH069_FINALIZE_RECEIPT.json \
 --isolation-register /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl \
 --formal-public /work/home/lilysharp/private/formal800_20261012/public/results \
 --published-research "$ROOT/input/published_research" \
 --global-t4 "$ROOT/input/global_t4" \
 --output "$ROOT/public" --private-output "$ROOT/private"
