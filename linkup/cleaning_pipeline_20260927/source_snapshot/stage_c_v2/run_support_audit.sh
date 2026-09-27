#!/bin/bash
#SBATCH --job-name=linkup_support_audit
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/support-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/support-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=32
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/support_audit.py --config /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/support_config.json
