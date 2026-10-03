#!/bin/bash
#SBATCH --job-name=linkup-p4-select
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/p4-select-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/p4-select-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
CODE="$ROOT/code/pre_revelio_execution_v1"
AUDIT="$ROOT/private/comparison_join_v1/GLOBAL_JOB_HASH_AUDIT.json"
NARROW_RECEIPT="$ROOT/private/semantic_narrow_v1/BATCH_RECEIPT.json"
META="$ROOT/private/human_review_pack_20261003/full_verified_review_index.metadata.json"
python "$CODE/build_p4_frame_metadata.py" --audit "$AUDIT" --narrow-receipt "$NARROW_RECEIPT" --output "$META" --expected-canonical-rows 204774035 --verified-usable-rows 204768752
python "$CODE/human_review/build_blind_review_pack.py" \
 --frame-parquet "$ROOT/private/semantic_narrow_v1/shards" \
 --duplicate-job-hash-parquet "$ROOT/private/comparison_join_v1/duplicate_job_hashes" \
 --frame-metadata "$META" --allow-unverified-heldout-d18 \
 --known-used-key-manifest "$ROOT/private/human_review_pack_20261003/known_prior_review_keys_d18.json" \
 --reviewer-schema "$CODE/reviewer_pack_schema.json" \
 --private-output-dir "$ROOT/private/human_review_pack_20261003" \
 --public-receipt "$ROOT/results/human_review/ACTUAL_PACK_RECEIPT.json" --repo-root "$CODE"
