#!/bin/bash
#SBATCH --job-name=f10k-b2-4-final
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch002_004/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch002_004/logs/%x_%j.err
# Site module initialization may return nonzero while setting up shell hooks.
# Match the existing successful baseline environment entry; fail explicitly on load.
set +e
set +u
set -o pipefail
printf 'wrapper_start batch=%s\n' "${1:-missing}"
source /etc/profile
module load python/3.8.10
runtime_rc=$?
if [ "$runtime_rc" -ne 0 ]; then
  printf 'python module load failed rc=%s\n' "$runtime_rc" >&2
  exit "$runtime_rc"
fi
set -e
trap 'rc=$?; printf "wrapper_error line=%s rc=%s\n" "$LINENO" "$rc" >&2' ERR
python3 --version
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077

if [ "$#" -ne 6 ]; then
  echo "usage: sbatch wz_finalize_batch002_004.sbatch BATCH_NUMBER REVIEW_01 ... REVIEW_05" >&2
  exit 2
fi
BATCH_NUMBER="$1"
shift
if [ "$BATCH_NUMBER" -lt 2 ] || [ "$BATCH_NUMBER" -gt 4 ]; then
  echo "BATCH_NUMBER must be 2, 3, or 4" >&2
  exit 2
fi

ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
COV=/work/home/lilysharp/private/production_coverage_20261017
FORMAL=/work/home/lilysharp/private/formal800_20261012
CODE="$ROOT/code/finalize_batch002_004.py"
BATCH=$(printf '%03d' "$BATCH_NUMBER")
OUT="$ROOT/private/batch002_004/batch$BATCH"
mkdir -p "$ROOT/private/batch002_004/logs" "$OUT/validator_packets" "$OUT/validated" "$OUT/final" "$ROOT/public" "$ROOT/receipts"

if [ "$BATCH_NUMBER" -eq 2 ]; then
  PRIOR="$ROOT/private/batch001/final"
  PRIOR_RECEIPT="$ROOT/receipts/BATCH001_FINALIZE_RECEIPT.json"
else
  PREV=$(printf '%03d' $((BATCH_NUMBER - 1)))
  PRIOR="$ROOT/private/batch002_004/batch$PREV/final"
  PRIOR_RECEIPT="$ROOT/receipts/BATCH${PREV}_FINALIZE_RECEIPT.json"
fi

reviews=("$@")
validated=()
receipts=()
validation_failed=0
for n in 01 02 03 04 05; do
  packet="$OUT/packets/PACKET_${n}_PRIVATE.jsonl"
  core="$OUT/validator_packets/CORE_PACKET_${n}_PRIVATE.jsonl"
  valid="$OUT/validated/VALIDATED_PACKET_${n}_PRIVATE.jsonl"
  errors="$OUT/validated/VALIDATION_ERRORS_PACKET_${n}_PRIVATE.jsonl"
  receipt="$ROOT/receipts/BATCH${BATCH}_VALIDATION_RECEIPT_PACKET_${n}.json"
  python3 "$CODE" core-packet --batch-number "$BATCH_NUMBER" --enriched-packet "$packet" --output "$core" --expected-records 20
  index=$((10#$n - 1))
  if python3 "$FORMAL/code/validate_reviews.py" --packet "$core" --reviews "${reviews[$index]}" \
    --schema "$FORMAL/code/FORMAL800_REVIEW_SCHEMA.json" --private-validated "$valid" \
    --private-errors "$errors" --public-receipt "$receipt" --expected-records 20; then
    :
  else
    validation_failed=1
    printf "validation_failed packet=%s errors=%s\n" "$n" "$errors" >&2
  fi
  validated+=("$valid")
  receipts+=("$receipt")
done
if [ "$validation_failed" -ne 0 ]; then
  exit 2
fi
# Permit the same required validators to finish while a prior batch is repaired.
if [ "${VALIDATION_ONLY:-0}" = "1" ]; then
  exit 0
fi

all="$OUT/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl"
all_packets="$OUT/packets/PACKETS_ALL100_PRIVATE.jsonl"
: > "$all"
: > "$all_packets"
for index in "${!validated[@]}"; do
  cat "${validated[$index]}" >> "$all"
  n=$(printf '%02d' $((index + 1)))
  cat "$OUT/packets/PACKET_${n}_PRIVATE.jsonl" >> "$all_packets"
done

python3 "$CODE" finalize --batch-number "$BATCH_NUMBER" \
  --enriched-packet "$all_packets" --validated-reviews "$all" \
  --validation-receipts "${receipts[@]}" --validated-packets "${validated[@]}" \
  --coverage-module "$COV/code/reconcile_coverage.py" --prior-receipt "$PRIOR_RECEIPT" \
  --existing-ledger "$PRIOR/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --existing-queue "$PRIOR/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --existing-uncertainty "$PRIOR/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --private-ledger "$OUT/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --private-queue "$OUT/final/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --private-uncertainty "$OUT/final/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" \
  --public-counts "$ROOT/public/BATCH${BATCH}_RESULTS_PUBLIC.json" \
  --receipt "$ROOT/receipts/BATCH${BATCH}_FINALIZE_RECEIPT.json"
