#!/bin/bash
#SBATCH --job-name=linkup-first3-pre
#SBATCH --partition=hx1hdnormal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/fixed3-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/fixed3-%j.err
set -euo pipefail
module load anaconda3/2023.09
python /public/home/lilysharp/linkup_analysis_execution_oct02/code/run_fixed3_pre_gate.py \
  --manifest /public/home/lilysharp/linkup_analysis_execution_oct02/private/fixed3_manifest.jsonl \
  --builder /public/home/lilysharp/linkup_analysis_execution_oct02/code/build_release_first_tables.py \
  --output /public/home/lilysharp/linkup_analysis_execution_oct02/results/fixed3_pre_gate_v1
