#!/bin/bash
#SBATCH --job-name=lk-pro-packets
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/relation_channel_20261025/logs/packets-%j.out
#SBATCH --error=/work/home/lilysharp/private/relation_channel_20261025/logs/packets-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module purge
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/work/home/lilysharp/private/relation_channel_20261025
python "$R/code/prepare_pro_packets.py" \
  --request-dir "$R/review_request_v1" \
  --inputs /work/home/lilysharp/private/year_object_relation_20261024/inputs_v1 \
  --recovered /work/home/lilysharp/private/linkup_relation_feasibility_20261024/recovered \
  --contexts-per-packet 24 --output "$R/pro_packets_v1"
