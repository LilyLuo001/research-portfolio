#!/bin/bash
#SBATCH --job-name=lk-pro-next3
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
python "$R/code/prepare_packets.py" \
 --catalog /public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl \
 --reference /public/home/lilysharp/linkup_metadata_research_20261026/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet \
 --raw-roots /public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions \
 --normalizer "$R/code/legacy_v5_frozen.py" \
 --private-output "$R/batch003/private" --public-output "$R/batch003/public" --count 60 \
 --start-shard 1 --start-row 120 --prior-manifests "$R/batch001/private/PACKET_MANIFEST_PRIVATE.jsonl" "$R/batch002/private/PACKET_MANIFEST_PRIVATE.jsonl"
