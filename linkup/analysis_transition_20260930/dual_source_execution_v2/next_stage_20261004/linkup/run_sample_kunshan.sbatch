#!/bin/bash
#SBATCH --job-name=linkup-next-sample
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=10G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/next-sample-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/next-sample-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
CODE=${ROOT}/code/next_stage_20261004/linkup
OUT=${ROOT}/private/next_stage_20261004/linkup/run-${SLURM_JOB_ID}
PUBLIC=${ROOT}/results/next_stage_20261004/linkup/run-${SLURM_JOB_ID}
umask 077
mkdir -p "${OUT}" "${PUBLIC}"
python "${CODE}/build_fixed_research_sample.py" \
  --frozen-formal "${ROOT}/private/dual_source_execution_v2/linkup_sample/run-123584403/L1_FORMAL_SAMPLE_KEYS_PRIVATE.parquet" \
  --joined-dir "${ROOT}/private/comparison_join_v1/joined" \
  --private-output "${OUT}" --public-output "${PUBLIC}" \
  --threads 4 --memory-limit 8GB
