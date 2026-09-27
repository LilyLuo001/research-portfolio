#!/bin/bash
#SBATCH --job-name=text_v3_kunshan
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v3/logs/v3-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v3/logs/v3-%j.err
set -euo pipefail
module load python/3.8.10
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_c_v3
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/check_portability.py --input /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/portability_input.jsonl --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/outputs/portability-${SLURM_JOB_ID} --workers 16
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:/public/home/lilysharp/linkup_analysis_v1/stage_c_v3
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/compare_pilot.py --sample /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/sample_ads.parquet --v1 /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/outputs/text-v2-123126470/candidate_features_v2.parquet --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/outputs/pilot-${SLURM_JOB_ID} --workers 16
