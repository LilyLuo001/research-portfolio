#!/bin/bash
#SBATCH --job-name=lk-pro-checkpoint
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/relation_channel_20261025/logs/review-qa-%j.out
#SBATCH --error=/work/home/lilysharp/private/relation_channel_20261025/logs/review-qa-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module purge
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/work/home/lilysharp/private/relation_channel_20261025
python "$R/code/validate_and_checkpoint.py" \
  --packet-root "$R/pro_packets_v1" --reviews "$R/reviews_v1" \
  --manifest-sha256 "${1:?Pass actual frozen PACKET_MANIFEST_PUBLIC.json SHA256}"
