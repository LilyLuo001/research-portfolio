#!/bin/bash
# Submit with one explicit PREFIX. Production uses 32 CPU/96G on the free queue.
#SBATCH --job-name=linkup-disposition-prefix
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=1-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-prefix-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-prefix-%j.err
set -euo pipefail
: "${PREFIX:?submit with --export=ALL,PREFIX=<one lowercase hex character>}"
case "${PREFIX}" in [0-9a-f]) ;; *) echo "invalid PREFIX" >&2; exit 2 ;; esac
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
/public/software/apps/python/3.8.10/bin/python3 "${ROOT}/prepare_release_dispositions.py" prefix \
  --config "${ROOT}/config_disposition_kunshan.json" --prefix "${PREFIX}"
