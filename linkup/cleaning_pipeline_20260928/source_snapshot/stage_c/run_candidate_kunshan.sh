#!/bin/bash
#SBATCH --job-name=linkup_stage_c_candidates
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c/logs/candidate-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c/logs/candidate-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:/public/home/lilysharp/linkup_analysis_v1/stage_c
export OMP_NUM_THREADS=1
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c/extract_sample.py \
  --sample /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/sample_ads.parquet \
  --out /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/candidate_pilot \
  --workers 16
