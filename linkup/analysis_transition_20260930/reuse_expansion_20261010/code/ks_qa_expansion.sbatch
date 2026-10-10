#!/bin/bash
#SBATCH --job-name=d67-iqa
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/qa-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/qa-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/qa_expansion.py" --global-manifest "$ROOT/private/final/GLOBAL_OUTPUT_MANIFEST_PRIVATE.json" --public-dir "$ROOT/public/final" --run-receipt "$ROOT/public/final/RUN_RECEIPT_PUBLIC.json" --output "$ROOT/public/final/INDEPENDENT_QA_PUBLIC.json"
