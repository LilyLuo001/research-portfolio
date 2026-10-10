#!/bin/bash
#SBATCH --job-name=d63_first5_compare
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/run-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/run-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis
python3 "$ROOT/code/build_first5_comparison.py" \
  --manifest "$ROOT/private/FIRST5_INPUT_MANIFEST_PRIVATE.json" \
  --metadata /public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/output_fast/FIRST5_METADATA_FAST_PRIVATE.parquet \
  --metadata-qa "$ROOT/input_public/FIRST5_METADATA_FAST_QA_PUBLIC.json" \
  --decision "$ROOT/input_public/ROOT_D63_ANALYSIS_DECISION.json" \
  --output "$ROOT/public"
