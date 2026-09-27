#!/bin/bash
#SBATCH --job-name=linkup_text_v2
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/text-v2-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/text-v2-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:/public/home/lilysharp/linkup_analysis_v1/stage_c_v2
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/compare_pilot.py \
 --sample /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/sample_ads.parquet \
 --v1 /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/candidate_pilot/candidate_features.parquet \
 --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/outputs/text-v2-${SLURM_JOB_ID} \
 --workers 16
