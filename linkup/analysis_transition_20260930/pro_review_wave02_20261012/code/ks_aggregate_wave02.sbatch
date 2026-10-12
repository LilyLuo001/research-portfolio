#!/bin/bash
#SBATCH --job-name=pro-wave02-agg
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/aggregate-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/aggregate-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
D67=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/aggregate_wave02_before_after.py" --global-manifest "$D67/private/final/GLOBAL_OUTPUT_MANIFEST_PRIVATE.json" \
 --frozen-manifest "$D67/private_input/D67_FROZEN_69_PRIVATE.json" --closing-root "$D67/private/closing_projection_ks" \
 --review-overlay "$ROOT/private/WAVE02_REVIEW_OVERLAY_PRIVATE.jsonl" \
 --validation-receipt "$ROOT/public/WAVE02_REVIEW_VALIDATION_RECEIPT_PUBLIC.json" \
 --selection-receipt "$ROOT/public/selection/RUN_RECEIPT_PUBLIC.json" --output "$ROOT/public/final"
