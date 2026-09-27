#!/bin/bash
#SBATCH --job-name=text_v4_kunshan
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v4/logs/v4-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v4/logs/v4-%j.err
set -euo pipefail
module load python/3.8.10
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_c_v4
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/check_portability.py --input /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/portability_input.jsonl --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/outputs/portability-${SLURM_JOB_ID} --workers 16
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:/public/home/lilysharp/linkup_analysis_v1/stage_c_v4
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/compare_pilot.py --sample /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/sample_ads.parquet --v1 /public/home/lilysharp/linkup_analysis_v1/stage_c_v3/outputs/pilot-123129049/candidate_features_v3.parquet --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/outputs/pilot-${SLURM_JOB_ID} --workers 16
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/export_research_candidates.py --sample /public/home/lilysharp/linkup_analysis_v1/stage_c/kunshan_sample_v1_20260925/sample_ads.parquet --candidates /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/outputs/pilot-${SLURM_JOB_ID}/candidate_features_v4.parquet --parser-source /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/requirement_candidates.py --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v4/outputs/research-${SLURM_JOB_ID}
