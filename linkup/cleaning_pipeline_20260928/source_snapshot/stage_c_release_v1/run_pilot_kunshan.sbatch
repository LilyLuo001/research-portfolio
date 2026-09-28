#!/bin/bash
#SBATCH --job-name=linkup_release_pilot
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/pilot-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/pilot-%j.err
set -euo pipefail
module load python/3.8.10 2>/dev/null || module load python/3.8.12
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_analysis_v1
OUT=${ROOT}/stage_c_release_v1/outputs/kunshan_100k_v1
test ! -e "${OUT}"
python3 "${ROOT}/stage_c_release_v1/lean_writer.py" \
  --source "${ROOT}/stage_c_v6_batch/outputs/kunshan_sample_v1/selected_ads_with_text.parquet" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${ROOT}/stage_c_release_v1/enrichment.py" \
  --output-dir "${OUT}" --workers 8 --output-cap-bytes 250000000
