#!/bin/bash
#SBATCH --job-name=pro-wave02-part
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/partition-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012/public/partition-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/pro_review_wave02_20261012
python3 "$ROOT/code/partition_wave02_packet.py" --packet "$ROOT/private/selection/WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl" \
 --schema "$ROOT/code/WAVE02_COMPACT_REVIEW_SCHEMA.json" --instructions "$ROOT/code/REVIEW_INSTRUCTIONS.md" \
 --private-output "$ROOT/private/review_partitions" --public-output "$ROOT/public/selection"
