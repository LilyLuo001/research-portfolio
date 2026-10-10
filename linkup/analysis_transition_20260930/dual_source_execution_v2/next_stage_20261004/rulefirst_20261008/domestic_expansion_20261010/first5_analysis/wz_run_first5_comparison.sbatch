#!/bin/bash
#SBATCH --job-name=d63_first5_compare
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/run-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis/logs/run-%j.err
source /etc/profile
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis
python3 "$ROOT/code/build_first5_comparison.py" --manifest "$ROOT/private/FIRST5_INPUT_MANIFEST_PRIVATE.json" --metadata "$ROOT/private_source/continuation_20261010/metadata_join_first5_d60/output_fast/FIRST5_METADATA_FAST_PRIVATE.parquet" --metadata-qa "$ROOT/input_public/FIRST5_METADATA_FAST_QA_PUBLIC.json" --decision "$ROOT/input_public/ROOT_D63_ANALYSIS_DECISION.json" --output "$ROOT/public"
