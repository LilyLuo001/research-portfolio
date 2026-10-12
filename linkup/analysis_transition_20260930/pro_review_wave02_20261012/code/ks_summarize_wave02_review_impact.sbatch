#!/bin/bash
#SBATCH --job-name=pro-wave02-impact
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/impact-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/impact-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
python3 "$ROOT/code/summarize_wave02_review_impact.py" \
  --packet "$ROOT/private/selection/WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl" \
  --validated-overlay "$ROOT/private/WAVE02_REVIEW_OVERLAY_PRIVATE.jsonl" \
  --selection-counts "$ROOT/public/selection/KS13_FIELD_SPECIFIC_COUNTS_PUBLIC.csv" \
  --validation-receipt "$ROOT/public/WAVE02_REVIEW_VALIDATION_RECEIPT_PUBLIC.json" \
  --output "$ROOT/public/final/review_impact"
python3 "$ROOT/code/verify_wave02_aggregate_outputs.py" \
  --aggregate-dir "$ROOT/public/final" \
  --executed-code-archive "$ROOT/code/archive/aggregate_wave02_before_after_EXECUTED_124253429_432.py" \
  --postrun-source "$ROOT/code/aggregate_wave02_before_after.py" \
  --executed-code-sha256 d0243e760d689d472c1604ef1b4e982085998643ecdc00f909ae898682c35c0e \
  --postrun-source-sha256 7587bcb90812d7e05295aa8a89025fd224583d1b08bd3793ebc0f263cb9f0f14 \
  --output "$ROOT/public/final/AGGREGATE_OUTPUT_VERIFICATION_PUBLIC.json"
