#!/bin/bash
#SBATCH --job-name=lk-overlay-probe
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:03:00
#SBATCH --output=/work/home/lilysharp/private/reference_overlay_20261026/logs/probe-%j.out
#SBATCH --error=/work/home/lilysharp/private/reference_overlay_20261026/logs/probe-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module purge
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
python /work/home/lilysharp/private/reference_overlay_20261026/code/probe_sources.py --mode wz --output /work/home/lilysharp/private/reference_overlay_20261026/probe/WZ_PROBE_PUBLIC.json
