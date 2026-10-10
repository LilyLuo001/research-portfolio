#!/bin/bash
#SBATCH --job-name=d63_first5_qa
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/qa-%j.err
source /etc/profile
set -euo pipefail
module load python/3.8.10
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis
python3 "$ROOT/code/qa_first5_comparison.py" --public "$ROOT/public" --output "$ROOT/public/QA_PUBLIC.json"
