#!/bin/bash
#SBATCH --job-name=linkup_v6_recover
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v6_batch/logs/recover-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v6_batch/logs/recover-%j.err
set -euo pipefail
module load python/3.8.10 2>/dev/null || module load python/3.8.12
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_analysis_v1
SAMPLE=${ROOT}/stage_c_v6_batch/outputs/kunshan_sample_v1
COMPACT=${ROOT}/stage_c_v6_batch/outputs/kunshan_compact_v1
TABLES=${ROOT}/stage_c_v6_batch/outputs/kunshan_tables_v1
test -f "${SAMPLE}/SAMPLE_REPORT.json" && test -f "${SAMPLE}/selected_ads_with_text.parquet"
test ! -e "${COMPACT}" && test ! -e "${TABLES}"
python3 "${ROOT}/stage_c_v6_batch/run_compact_chunks.py" \
  --source "${SAMPLE}/selected_ads_with_text.parquet" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --output-dir "${COMPACT}" --workers 8 --output-cap-bytes 500000000
python3 "${ROOT}/stage_c_v6_batch/build_first_tables.py" \
  --sample-dir "${SAMPLE}" --compact-dir "${COMPACT}" --output-dir "${TABLES}"
