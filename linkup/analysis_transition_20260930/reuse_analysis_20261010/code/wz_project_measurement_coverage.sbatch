#!/bin/bash
#SBATCH --job-name=d66_measure_cov
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010/logs/coverage-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010/logs/coverage-%j.err
source /etc/profile
set +u
module load python/3.8.10
set -euo pipefail
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ARROW_NUM_THREADS=1
BASE=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010
python3 "$BASE/code/project_measurement_coverage.py" --overlay "$BASE/private/FIRST5_OLD_CURRENT_OVERLAY_PRIVATE.parquet" --public-dir "$BASE/public" --output "$BASE/public/MEASUREMENT_COVERAGE_PUBLIC.csv" --receipt "$BASE/public/MEASUREMENT_COVERAGE_RECEIPT_PUBLIC.json"
python3 "$BASE/code/qa_measurement_coverage.py" --overlay "$BASE/private/FIRST5_OLD_CURRENT_OVERLAY_PRIVATE.parquet" --coverage "$BASE/public/MEASUREMENT_COVERAGE_PUBLIC.csv" --receipt "$BASE/public/MEASUREMENT_COVERAGE_RECEIPT_PUBLIC.json" --output "$BASE/public/MEASUREMENT_COVERAGE_QA_PUBLIC.json"
