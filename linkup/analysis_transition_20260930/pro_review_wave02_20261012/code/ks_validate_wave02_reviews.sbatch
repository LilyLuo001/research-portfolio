#!/bin/bash
#SBATCH --job-name=pro-wave02-val
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/validate-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/validate-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/runtime_py38:/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
python3 "$ROOT/code/validate_wave02_reviews.py" \
  --packet "$ROOT/private/selection/WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl" \
  --review-a "$ROOT/private/WAVE02_REVIEW_A_FINAL.jsonl" \
  --review-b "$ROOT/private/WAVE02_REVIEW_B_FINAL.jsonl" \
  --schema "$ROOT/code/WAVE02_COMPACT_REVIEW_SCHEMA.json" \
  --private-overlay "$ROOT/private/WAVE02_REVIEW_OVERLAY_PRIVATE.jsonl" \
  --public-receipt "$ROOT/public/WAVE02_REVIEW_VALIDATION_RECEIPT_PUBLIC.json" \
  --expected-records 96
