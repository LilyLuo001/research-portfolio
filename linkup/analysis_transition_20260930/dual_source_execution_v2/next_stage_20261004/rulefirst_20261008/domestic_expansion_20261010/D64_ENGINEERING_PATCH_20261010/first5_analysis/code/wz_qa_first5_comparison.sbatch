#!/bin/bash
#SBATCH --job-name=d64-first5-qa
#SBATCH --partition=wzhdtest
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/first5_analysis/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/first5_analysis/logs/qa-%j.err
set -eo pipefail
umask 077
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
BASE=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010
PATCH_BASE="$BASE/d64_engineering_patch_20261010"
python3 "$PATCH_BASE/first5_analysis/code/qa_first5_comparison.py" --public "$BASE/first5_analysis/public" --output "$PATCH_BASE/first5_analysis/public/QA_PUBLIC.json"
