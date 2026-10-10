#!/bin/bash
#SBATCH --job-name=d67-mkey
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --array=5-12%4
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/mkey-%A_%a.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/mkey-%A_%a.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/project_current_keys.py" --manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" --index "$SLURM_ARRAY_TASK_ID" --output-root "$ROOT/metadata_69/private/input_keys_ks"
