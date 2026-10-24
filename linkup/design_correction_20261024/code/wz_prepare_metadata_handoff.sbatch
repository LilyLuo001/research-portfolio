#!/bin/bash
#SBATCH --job-name=lk-corr-meta
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/design_correction_20261024/logs/meta-%j.out
#SBATCH --error=/work/home/lilysharp/private/design_correction_20261024/logs/meta-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
python /work/home/lilysharp/private/design_correction_20261024/code/wz_prepare_metadata_handoff.py
