#!/bin/bash
#SBATCH --job-name=linkup_stage_c_sample
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c/logs/sample-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c/logs/sample-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=2
export ARROW_NUM_THREADS=2
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c/prepare_sample.py --config /public/home/lilysharp/linkup_analysis_v1/stage_c/config_kunshan.json
