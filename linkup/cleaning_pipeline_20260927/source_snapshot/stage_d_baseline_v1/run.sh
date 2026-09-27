#!/bin/bash
#SBATCH --job-name=stage_d_occ_base
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_d_baseline_v1/logs/run-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_d_baseline_v1/logs/run-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
python3 /public/home/lilysharp/linkup_analysis_v1/stage_d_baseline_v1/build_occupation_baseline.py --config /public/home/lilysharp/linkup_analysis_v1/stage_d_baseline_v1/config.json
