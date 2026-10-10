#!/bin/bash
#SBATCH --job-name=d67-agg
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/agg-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/agg-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/aggregate_expansion.py" --manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" \
 --wz-overlay-dir "$ROOT/private/additive_wz" --ks-overlay-dir "$ROOT/private/additive_ks" \
 --metadata69 "$ROOT/metadata_69/private/METADATA69_PRIVATE.parquet" \
 --metadata-receipt "$ROOT/metadata_69/public/METADATA69_RECEIPT_PUBLIC.json" \
 --metadata-qa "$ROOT/metadata_69/public/METADATA69_QA_PUBLIC.json" \
 --private-output "$ROOT/private/final" --public-output "$ROOT/public/final"
