#!/bin/bash
#SBATCH --job-name=text_v3_wuzhen
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/linkup_analysis_v1/stage_c_v3/logs/v3-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_analysis_v1/stage_c_v3/logs/v3-%j.err
#SBATCH --gres=dcu:Hygon:1
set -euo pipefail
module load python/3.8.10
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/work/home/lilysharp/linkup_analysis_v1/stage_c_v3
python3 /work/home/lilysharp/linkup_analysis_v1/stage_c_v3/check_portability.py --input /work/home/lilysharp/linkup_analysis_v1/stage_c_v3/portability_input.jsonl --out /work/home/lilysharp/linkup_analysis_v1/stage_c_v3/outputs/portability-${SLURM_JOB_ID} --workers 8
