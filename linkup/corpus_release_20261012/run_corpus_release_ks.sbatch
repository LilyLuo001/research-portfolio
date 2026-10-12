#!/bin/bash
#SBATCH --job-name=linkup-release
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/logs/release-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/logs/release-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
RELEASE_ROOT=${ROOT}/corpus_release_20261012
mkdir -p "${RELEASE_ROOT}/logs"
python "${RELEASE_ROOT}/code/build_corpus_release.py" \
  --source-root "${ROOT}/private/semantic_narrow_v1" \
  --t1-dir "${RELEASE_ROOT}/input/t1_public" \
  --t4-dir "${ROOT}/results/T4_full_v3" \
  --t4-receipt "${ROOT}/results/T4_full_v3/T4_RECEIPT.json" \
  --candidate-join-manifest "${ROOT}/private/comparison_join_v1/JOIN_MANIFEST.json" \
  --output-root "${RELEASE_ROOT}/private/release_v1"
