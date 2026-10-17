#!/bin/bash
#SBATCH --job-name=researchcmp1013
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/research_results_20261013/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/research_results_20261013/logs/%x_%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077
W=/work/home/lilysharp/private/research_results_20261013
F=/work/home/lilysharp/private/formal800_20261012
mkdir -p "$W/logs" "$W/results"
python3 "$W/code/analyze_research_comparisons.py" \
  --ad-level "$F/private/final/AD_LEVEL_MEASURES.parquet" \
  --validated-reviews "$F/private/validation/final/validated_reviews.jsonl" \
  --existing-q1 "$F/public/results/COMPARISON_1_EXPERIENCE.csv" \
  --existing-results "$F/public/results" \
  --output-dir "$W/results"
