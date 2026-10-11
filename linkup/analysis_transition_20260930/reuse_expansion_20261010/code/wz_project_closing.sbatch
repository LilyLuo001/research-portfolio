#!/bin/bash
#SBATCH --job-name=d67-close-wz
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --array=0-13%4
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_expansion_20261010/public/closing-wz-%A_%a.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_expansion_20261010/public/closing-wz-%A_%a.err
set -eo pipefail
source /etc/profile
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/reuse_expansion_20261010
: "${OFFSET:?submit with --export=ALL,OFFSET=0|14|28|42}"
INDEX=$((OFFSET + SLURM_ARRAY_TASK_ID))
python3 "$ROOT/code/project_closing_evidence.py" --manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" --region wuzhen --index "$INDEX" --output-root "$ROOT/private/closing_projection"
