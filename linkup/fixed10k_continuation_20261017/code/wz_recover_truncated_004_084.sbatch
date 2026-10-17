#!/bin/bash
#SBATCH --job-name=f10k_trunc_recover
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
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
F=/work/home/lilysharp/private/formal800_20261012
mkdir -p "$T/private/continuation/logs" "$T/private/continuation/isolation"
python3 "$T/private/continuation/code/recover_truncated_004_084.py" \
  --claim-manifest "$T/private/batch002_004/CLAIM_MANIFEST_PRIVATE.jsonl" \
  --packet "$T/private/batch002_004/batch004/packets/PACKET_05_PRIVATE.jsonl" \
  --source-map "$H/run-123660254/fixed10000_wuzhen.source_map.jsonl" \
  --normalizer "$F/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py" \
  --attempt-marker "$T/private/continuation/isolation/TRUNCATED_004_084_ATTEMPT_STARTED.json" \
  --receipt "$T/private/continuation/isolation/TRUNCATED_004_084_RECOVERY_RECEIPT.json" \
  --isolation-register "$T/private/continuation/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl"
