#!/bin/bash
#SBATCH --job-name=linkup-l1-sample-v1
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=08:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/l1-sample-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/l1-sample-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
CODE=${ROOT}/code/dual_source_execution_v2/linkup_sample
OUT_BASE=${ROOT}/private/dual_source_execution_v2/linkup_sample
OUT=${OUT_BASE}/run-${SLURM_JOB_ID}
umask 077
mkdir -p "${OUT}"
chmod 700 "${OUT}"
JOB_TMP=${OUT}/duckdb_tmp-${SLURM_JOB_ID}
python "${CODE}/build_l1_sample.py" \
  --joined-dir "${ROOT}/private/comparison_join_v1/joined" \
  --narrow-dir "${ROOT}/private/semantic_narrow_v1/shards" \
  --known-used "${ROOT}/private/human_review_pack_20261003/known_prior_review_keys_d18.json" \
  --known-used "${ROOT}/private/human_review_pack_20261003/selected_key_manifest.json" \
  --output-dir "${OUT}" --threads 4 --memory-limit 6GB \
  --temp-dir "${JOB_TMP}"
