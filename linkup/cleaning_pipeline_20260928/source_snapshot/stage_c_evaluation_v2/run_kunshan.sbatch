#!/bin/bash
#SBATCH --job-name=stage_c_eval_v2
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_evaluation_v2/logs/eval-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_evaluation_v2/logs/eval-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=2
export ARROW_NUM_THREADS=2
cd /public/home/lilysharp/linkup_analysis_v1/stage_c_evaluation_v2
python3 prepare_evaluation_frame.py --config config_frame_kunshan.json
python3 finalize_annotation_pack.py --config config_finalize_kunshan.json
