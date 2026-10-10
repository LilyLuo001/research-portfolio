#!/bin/bash
#SBATCH --job-name=d67-add-ks
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --array=0-12%4
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/add-%A_%a.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/add-%A_%a.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/project_one_shard.py" \
  --manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" --region kunshan --index "$SLURM_ARRAY_TASK_ID" \
  --old-narrow-root "$ROOT/private/old_narrow" --old-v6-root "$ROOT/private/old_v6" --old-v6-inventory "$ROOT/private_input/HZ_V6_69_SHA_PRIVATE.json" \
  --output-root "$ROOT/private/additive_ks"
