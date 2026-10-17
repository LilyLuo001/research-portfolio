#!/bin/bash
#SBATCH --job-name=fx10k-b-opt
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/infer-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/infer-%j.err
set -eo pipefail
set +u
source /etc/profile
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
python /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/code/infer_shared_features.py
