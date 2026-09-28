#!/bin/bash
#SBATCH --job-name=linkup-disp-consolidate-par-v1
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=1-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-consolidate-par-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-consolidate-par-%j.err
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:${ROOT}
export ARROW_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/public/software/apps/python/3.8.10/bin/python3 "${ROOT}/parallel_consolidate_release_dispositions.py" \
  --config "${ROOT}/config_disposition_kunshan.json" \
  --workers 16 --intermediate-cap-bytes 17000000000 --free-reserve-bytes 8000000000
