#!/bin/bash
#SBATCH --job-name=f10k_trunc_record
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.err
set +e
set +u
source /etc/profile
module load python/3.8.10
rc=$?
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
set -eu
umask 077
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
H=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007
C="$T/private/continuation"
python3 "$C/code/finalize_failed_recovery.py" --attempt-marker "$C/isolation/TRUNCATED_004_084_ATTEMPT_STARTED.json" \
 --claim-manifest "$T/private/batch002_004/CLAIM_MANIFEST_PRIVATE.jsonl" --packet "$T/private/batch002_004/batch004/packets/PACKET_05_PRIVATE.jsonl" \
 --source-map "$H/run-123660254/fixed10000_wuzhen.source_map.jsonl" --failed-job-stderr "$C/logs/f10k_trunc_recover_46773992.err" \
 --receipt "$C/isolation/TRUNCATED_004_084_RECOVERY_RECEIPT.json" --isolation-register "$C/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl"
