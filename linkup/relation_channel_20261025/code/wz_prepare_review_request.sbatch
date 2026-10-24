#!/bin/bash
#SBATCH --job-name=lk-relation-request
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/relation_channel_20261025/logs/request-%j.out
#SBATCH --error=/work/home/lilysharp/private/relation_channel_20261025/logs/request-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module purge
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/work/home/lilysharp/private/relation_channel_20261025
python "$R/code/prepare_relation_review_request.py" \
  --inputs /work/home/lilysharp/private/year_object_relation_20261024/inputs_v1 \
  --output "$R/review_request_v1"
