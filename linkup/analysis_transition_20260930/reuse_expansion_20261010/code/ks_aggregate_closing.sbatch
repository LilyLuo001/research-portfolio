#!/bin/bash
#SBATCH --job-name=d67-close-agg
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/closing_package/agg-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/closing_package/agg-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
mkdir -p "$ROOT/public/closing_package"
python3 "$ROOT/code/aggregate_closing_package.py" \
 --global-manifest "$ROOT/private/final/GLOBAL_OUTPUT_MANIFEST_PRIVATE.json" \
 --frozen-manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" \
 --ks-projection "$ROOT/private/closing_projection_ks" --wz-projection "$ROOT/private/closing_projection_wz" \
 --common-support "$ROOT/public/final/COMMON_SUPPORT_PUBLIC.csv" --output "$ROOT/public/closing_package"
