#!/bin/bash
#SBATCH --job-name=lk-relation-inputs
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/relation_channel_20261025/logs/metadata-%j.out
#SBATCH --error=/work/home/lilysharp/private/relation_channel_20261025/logs/metadata-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module purge
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/work/home/lilysharp/private/relation_channel_20261025
P=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
printf '%s  %s\n' 48e8b0d01884424e286cd836bb37f198b9d52d3b74b029180994a5e0349c745e "$P/INPUT_MANIFEST_PRIVATE.json" | sha256sum -c -
python "$R/code/inventory_relation_metadata.py" \
  --recovered "$P/recovered" \
  --items-sha256 8a28fa07361c4eb56c6630941a8517c4a25f9766412e7519c34e43c76f71797e \
  --groups-sha256 132a6c5c870301b7bee736b66f942a187d7c408eaad466b6ae7cfffc382f11eb \
  --input-manifest "$P/INPUT_MANIFEST_PRIVATE.json" --output "$R/inventory_v1"
