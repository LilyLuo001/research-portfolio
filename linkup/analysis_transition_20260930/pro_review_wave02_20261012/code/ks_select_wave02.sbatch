#!/bin/bash
#SBATCH --job-name=pro-wave02-select
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/select-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/select-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
D67=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/select_wave02_packet.py" \
  --global-manifest "$D67/private/final/GLOBAL_OUTPUT_MANIFEST_PRIVATE.json" \
  --frozen-manifest "$D67/private_input/D67_FROZEN_69_PRIVATE.json" \
  --closing-root "$D67/private/closing_projection_ks" \
  --raw-root /public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions \
  --exclude-eval80 "$ROOT/private/input/EVAL80_SOURCE_PRIVATE.jsonl" \
  --exclude-prior /public/home/lilysharp/linkup_rulefirst_20261008/pro_review_20261012/private/input/DEV24_RELATION_DECISIONS_PRIVATE.jsonl \
  --private-output "$ROOT/private/selection" --public-output "$ROOT/public/selection"
