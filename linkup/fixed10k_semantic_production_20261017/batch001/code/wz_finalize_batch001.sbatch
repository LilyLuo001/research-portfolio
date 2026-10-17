#!/bin/bash
#SBATCH --job-name=f10k-b001-finalize
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/logs/%x_%j.err
set -eo pipefail
set +u
source /etc/profile
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077

# Submit only after all five reviewer files have been written.  The arguments
# are those five files in packet order; no template or partial output is valid.
if [ "$#" -ne 5 ]; then
  echo "usage: sbatch wz_finalize_batch001.sbatch REVIEW_01 ... REVIEW_05" >&2
  exit 2
fi
ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
COV=/work/home/lilysharp/private/production_coverage_20261017
FORMAL=/work/home/lilysharp/private/formal800_20261012
# The repository's batch001/code directory is staged into this release's
# existing remote $ROOT/code convention (as prepare_batch001.py was).
CODE="$ROOT/code/finalize_batch001.py"
OUT="$ROOT/private/batch001"
mkdir -p "$OUT/logs" "$OUT/validator_packets" "$OUT/validated" "$OUT/final" "$ROOT/public" "$ROOT/receipts"
PY=python3

reviews=("$@")
packets=()
validated=()
receipts=()
for n in 01 02 03 04 05; do
  packet="$OUT/packets/PACKET_${n}_PRIVATE.jsonl"
  core_packet="$OUT/validator_packets/CORE_PACKET_${n}_PRIVATE.jsonl"
  valid="$OUT/validated/VALIDATED_PACKET_${n}_PRIVATE.jsonl"
  errors="$OUT/validated/VALIDATION_ERRORS_PACKET_${n}_PRIVATE.jsonl"
  receipt="$ROOT/receipts/VALIDATION_RECEIPT_PACKET_${n}.json"
  "$PY" "$CODE" core-packet --enriched-packet "$packet" --output "$core_packet" --expected-records 20
  index=$((10#$n - 1))
  "$PY" "$FORMAL/code/validate_reviews.py" --packet "$core_packet" --reviews "${reviews[$index]}" \
    --schema "$FORMAL/code/FORMAL800_REVIEW_SCHEMA.json" --private-validated "$valid" \
    --private-errors "$errors" --public-receipt "$receipt" --expected-records 20
  packets+=("$packet"); validated+=("$valid"); receipts+=("$receipt")
done

all="$OUT/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl"
all_packets="$OUT/packets/PACKETS_ALL100_PRIVATE.jsonl"
: > "$all"
: > "$all_packets"
for index in "${!validated[@]}"; do
  cat "${validated[$index]}" >> "$all"
  cat "${packets[$index]}" >> "$all_packets"
done
"$PY" "$CODE" finalize \
  --enriched-packet "$all_packets" --validated-reviews "$all" \
  --validation-receipts "${receipts[@]}" --validated-packets "${validated[@]}" \
  --coverage-module "$COV/code/reconcile_coverage.py" \
  --existing-ledger "$COV/private/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --existing-queue "$COV/private/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --existing-uncertainty "$COV/private/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --private-ledger "$OUT/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --private-queue "$OUT/final/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --private-uncertainty "$OUT/final/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --public-counts "$ROOT/public/BATCH001_RESULTS_PUBLIC.json" \
  --receipt "$ROOT/receipts/BATCH001_FINALIZE_RECEIPT.json"
