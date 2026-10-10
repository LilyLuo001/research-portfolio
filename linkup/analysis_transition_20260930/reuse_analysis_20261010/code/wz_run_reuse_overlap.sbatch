#!/bin/bash
#SBATCH --job-name=d66_reuse_overlap
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=01:00:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010/logs/run-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010/logs/run-%j.err
source /etc/profile
set +u
module load python/3.8.10
set -euo pipefail
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ARROW_NUM_THREADS=1
BASE=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_analysis_20261010
FIRST5=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/first5_analysis
mkdir -p "$BASE/private" "$BASE/public" "$BASE/logs"
chmod 700 "$BASE/private" "$BASE/private_source"
python3 "$BASE/code/build_reuse_overlap.py" \
  --current-manifest "$FIRST5/private/FIRST5_INPUT_MANIFEST_PRIVATE.json" \
  --metadata "$FIRST5/private_source/continuation_20261010/metadata_join_first5_d60/output_fast/FIRST5_METADATA_FAST_PRIVATE.parquet" \
  --old-stage "$BASE/private_source/old_hz_first5" \
  --contract "$BASE/input_public/ROOT_EXECUTION_CONTRACT.json" \
  --private-output "$BASE/private" \
  --public-output "$BASE/public"
python3 "$BASE/code/qa_reuse_overlap.py" \
  --private-overlay "$BASE/private/FIRST5_OLD_CURRENT_OVERLAY_PRIVATE.parquet" \
  --public-dir "$BASE/public" \
  --output "$BASE/public/QA_PUBLIC.json"
