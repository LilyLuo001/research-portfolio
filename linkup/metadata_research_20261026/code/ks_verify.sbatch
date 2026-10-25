#!/bin/bash
#SBATCH --job-name=lk-meta-qa
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_metadata_research_20261026/logs/qa-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_metadata_research_20261026/logs/qa-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=1
R=/public/home/lilysharp/linkup_metadata_research_20261026
python "$R/code/verify_outputs.py" \
 --original-bridge /public/home/lilysharp/linkup_design_correction_20261024/run001/private/AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet \
 --research "$R/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet" \
 --join-receipt "$R/run001/public/METADATA_JOIN_RECEIPT_PUBLIC.json" \
 --comparison-private "$R/run001/comparison_private/CELL_SUPPORT_RESULTS_WEIGHTS_PRIVATE.csv" \
 --comparison-public "$R/run001/comparison_public/Q1_Q2_DESCRIPTIVE_RESULTS.csv" \
 --output "$R/run001/public/NUMERIC_ACCEPTANCE_PUBLIC.json"
