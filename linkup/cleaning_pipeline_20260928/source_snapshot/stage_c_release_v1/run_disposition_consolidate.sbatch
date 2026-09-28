#!/bin/bash
#SBATCH --job-name=linkup-disp-consolidate-v1
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=1-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-consolidate-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-consolidate-%j.err
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:${ROOT}
/public/software/apps/python/3.8.10/bin/python3 "${ROOT}/consolidate_release_dispositions.py" \
  --config "${ROOT}/config_disposition_kunshan.json"
