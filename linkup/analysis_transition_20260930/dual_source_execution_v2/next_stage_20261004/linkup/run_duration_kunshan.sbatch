#!/bin/bash
#SBATCH --job-name=linkup-next-years
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=10G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/next-years-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/next-years-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
CODE=${ROOT}/code/next_stage_20261004/linkup
SAMPLE_RUN=${SAMPLE_RUN:?set SAMPLE_RUN to the completed sample Slurm job id}
SAMPLE=${ROOT}/private/next_stage_20261004/linkup/run-${SAMPLE_RUN}/FIXED_RESEARCH_SAMPLE_KEYS_PRIVATE.parquet
SAMPLE_RECEIPT=${ROOT}/results/next_stage_20261004/linkup/run-${SAMPLE_RUN}/SAMPLE_EXECUTION_RECEIPT.json
OUT=${ROOT}/results/next_stage_20261004/linkup/duration-from-${SAMPLE_RUN}-${SLURM_JOB_ID}
umask 077
mkdir -p "${OUT}"
python "${CODE}/summarize_sample_durations.py" \
  --sample "${SAMPLE}" \
  --sample-receipt "${SAMPLE_RECEIPT}" \
  --duration-glob "${ROOT}/private/semantic_narrow_v1/shards/*.durations.parquet" \
  --output-dir "${OUT}" --threads 4 --memory-limit 8GB
