#!/bin/bash
#SBATCH --job-name=lk-pro-independent024
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/prepare-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/prepare-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
for n in 24; do
  printf -v B 'batch%03d' "$n"
  printf -v P 'batch%03d' "$((n-1))"
  read -r start_shard start_row < <(python -c 'import json,sys; d=json.load(open(sys.argv[1])); c=d["next_cursor"]; print(c["shard_ordinal"],c["row_offset"])' "$R/$P/public/PACKET_PREPARATION_PUBLIC.json")
  prior=()
  for ((i=1; i<n; i++)); do
    printf -v prior_batch 'batch%03d' "$i"
    prior+=("$R/$prior_batch/private/PACKET_MANIFEST_PRIVATE.jsonl")
  done
  python "$R/code/prepare_packets.py" \
    --catalog /public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl \
    --reference /public/home/lilysharp/linkup_metadata_research_20261026/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet \
    --raw-roots /public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions "$R/restored_raw_private" \
    --normalizer "$R/code/legacy_v5_frozen.py" \
    --private-output "$R/$B/private" --public-output "$R/$B/public" --count 720 \
    --start-shard "$start_shard" --start-row "$start_row" --prior-manifests "${prior[@]}"
done
