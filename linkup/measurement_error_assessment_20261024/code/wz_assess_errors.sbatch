#!/bin/bash
#SBATCH --job-name=lk_error_assess
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/error_assessment_20261024/logs/%x-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/error_assessment_20261024/logs/%x-%j.err
set -eo pipefail
source /etc/profile
set -u
module load apps/anaconda3/2023.09
export LC_ALL=C LANG=C OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/error_assessment_20261024
python "$ROOT/code/assess_existing_errors.py" \
 --joined /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/private/AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet \
 --q1 /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/public/T5_Q1_DIRECT_COMPARISONS.csv \
 --baseline "$ROOT/input/FINAL_FIELD_ADJUDICATION_PUBLIC.csv" \
 --old-diagnostic "$ROOT/input/AI_REVIEW_EXPERIENCE_AGREEMENT.csv" \
 --output "$ROOT/public"
