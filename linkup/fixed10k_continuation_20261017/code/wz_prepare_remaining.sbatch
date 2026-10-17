#!/bin/bash
#SBATCH --job-name=f10k_prep_015_069
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.err
set +e; set +u; source /etc/profile; module load python/3.8.10; rc=$?; if [ "$rc" -ne 0 ]; then exit "$rc"; fi
set -eu
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
umask 077
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017; H=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007; F=/work/home/lilysharp/private/formal800_20261012; P="$T/private/batch002_004/batch004/final"; C="$T/private/continuation"
python3 "$C/code/prepare_continuation.py" --queue "$P/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" --ledger "$P/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" --uncertainty "$P/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" --prior-receipt "$T/receipts/BATCH004_FINALIZE_RECEIPT.json" --frame "$H/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet" --normalizer "$F/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py" --formal-schema "$F/code/FORMAL800_REVIEW_SCHEMA.json" --formal-instructions "$T/code/REVIEW_INSTRUCTIONS.md" --formal-validator "$F/code/validate_reviews.py" --isolation-register "$C/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl" --recovery-receipt "$C/isolation/TRUNCATED_004_084_RECOVERY_RECEIPT.json" --private-output "$C/prepared" --public-receipt "$C/CONTINUATION_PREP_015_069_RECEIPT.json" --holdout-private "$C/splits/FINAL_EVALUATION_HOLDOUT_PRIVATE.jsonl" --holdout-expected-sha 5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1 --first-batch 15 --batch-count 55 --work-offset 1000 --context-count 5499 --manifest-name CLAIM_MANIFEST_BATCH015_069_PRIVATE.jsonl --repository-commit 4ed88d30b6f2541f3f2eb5dee92eb8cb5b8142c1
