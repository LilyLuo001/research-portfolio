#!/bin/bash
#SBATCH --job-name=lk-meta-compare
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_metadata_research_20261026/logs/run-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_metadata_research_20261026/logs/run-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 MKL_NUM_THREADS=1
R=/public/home/lilysharp/linkup_metadata_research_20261026
test ! -e "$R/run001/comparison_public/COMPARISON_RECEIPT_PUBLIC.json" || { echo completed_metadata_comparison_guard; exit 0; }
cd "$R/code"
if [ ! -e "$R/run001/public/METADATA_JOIN_RECEIPT_PUBLIC.json" ]; then
    python join_metadata.py \
      --bridge /public/home/lilysharp/linkup_design_correction_20261024/run001/private/AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet \
      --bridge-receipt /public/home/lilysharp/linkup_design_correction_20261024/run001/public/RUN_RECEIPT_PUBLIC.json \
      --candidate-dir /public/home/lilysharp/linkup_analysis_execution_oct02/private/comparison_join_v1/joined \
      --records-index /public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1 \
      --raw-records-dir /public/home/lilysharp/dewey_downloads/data/linkup_job_records \
      --private-output "$R/run001/private" --public-output "$R/run001/public"
fi
python compare_support.py \
  --input "$R/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet" \
  --join-receipt "$R/run001/public/METADATA_JOIN_RECEIPT_PUBLIC.json" \
  --spec "$R/COMPARISON_SPEC_PUBLIC.json" \
  --private-output "$R/run001/comparison_private" --public-output "$R/run001/comparison_public"
