#!/bin/bash
#SBATCH --job-name=f10k_trunc_inspect
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.err
set +e
set +u
set -o pipefail
source /etc/profile
module load python/3.8.10
runtime_rc=$?
if [ "$runtime_rc" -ne 0 ]; then exit "$runtime_rc"; fi
set -eu
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
umask 077
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
H=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007
mkdir -p "$T/private/continuation/logs" "$T/private/continuation/inspection"
python3 "$T/private/continuation/code/inspect_truncated_source.py" \
  --claim-manifest "$T/private/batch002_004/CLAIM_MANIFEST_PRIVATE.jsonl" \
  --source-map "$H/run-123660254/fixed10000_wuzhen.source_map.jsonl" \
  --frame "$H/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet" \
  --output "$T/private/continuation/inspection/TRUNCATED_004_084_STRUCTURE.json"
