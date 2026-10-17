#!/bin/bash
#SBATCH --job-name=fx10k-base-final
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/finalize-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/finalize-%j.err
set -eo pipefail
set +u
source /etc/profile
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
python /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/code/finalize_baseline_result.py
