#!/bin/bash
#SBATCH --job-name=linkup-fixed3-keys
#SBATCH --partition=hx1hdnormal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/fixed3-keys-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/fixed3-keys-%j.err
set -euo pipefail
module load anaconda3/2023.09
python /public/home/lilysharp/linkup_analysis_execution_oct02/code/project_fixed3_keys.py
