#!/bin/bash
#SBATCH --job-name=pro-review-validate
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_20261012/public/validate-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_20261012/public/validate-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u

ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_20261012
mkdir -p "$ROOT/private/output" "$ROOT/public"
umask 077
cat "$ROOT/private/input/REVIEW_SOL_A_REVISED.jsonl" \
    "$ROOT/private/input/REVIEW_SOL_B_REVISED.jsonl" \
    > "$ROOT/private/input/PRO_REVIEW_BATCH01_PRIVATE.jsonl.tmp"
mv "$ROOT/private/input/PRO_REVIEW_BATCH01_PRIVATE.jsonl.tmp" \
   "$ROOT/private/input/PRO_REVIEW_BATCH01_PRIVATE.jsonl"
python3 "$ROOT/code/validate_append_pro_review.py" \
  --packet "$ROOT/private/input/DEV24_RELATION_DECISIONS_PRIVATE.jsonl" \
  --reviews "$ROOT/private/input/PRO_REVIEW_BATCH01_PRIVATE.jsonl" \
  --firstpass-a "$ROOT/private/input/REVIEW_SOL_A.jsonl" \
  --firstpass-b "$ROOT/private/input/REVIEW_SOL_B.jsonl" \
  --revised-a "$ROOT/private/input/REVIEW_SOL_A_REVISED.jsonl" \
  --revised-b "$ROOT/private/input/REVIEW_SOL_B_REVISED.jsonl" \
  --changes-a "$ROOT/private/input/ROOT_REQUESTED_CHANGES_A_PRIVATE.json" \
  --changes-b "$ROOT/private/input/ROOT_REQUESTED_CHANGES_B_PRIVATE.json" \
  --root-spotcheck "$ROOT/private/input/ROOT_INDEPENDENT_SPOTCHECK_PRIVATE.json" \
  --root-acceptance "$ROOT/public/ROOT_BATCH01_ACCEPTANCE_PUBLIC.json" \
  --review-schema "$ROOT/private/input/JOINT_SCHEMA.json" \
  --expected-selection-numbers 2,3,4,6,7,8,10,11,12,14,15,16,18,19 \
  --previously-full-selection-numbers 1,5,13,17 \
  --previously-partial-selection-numbers 9 \
  --output-overlay "$ROOT/private/output/PRO_SEMANTIC_REVIEW_OVERLAY_PRIVATE.jsonl" \
  --output-coverage "$ROOT/private/output/PRO_REVIEW_BATCH_COVERAGE_PRIVATE.jsonl" \
  --private-summary "$ROOT/private/output/PRO_REVIEW_BATCH_SUMMARY_PRIVATE.json" \
  --public-receipt "$ROOT/public/PRO_REVIEW_VALIDATION_RECEIPT_PUBLIC.json" \
  --public-summary "$ROOT/public/PRO_REVIEW_BATCH01_SUMMARY_PUBLIC.json"
