#!/bin/bash
#SBATCH --job-name=f10k-cont-final
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.err
set +e; set +u; set -o pipefail
source /etc/profile
module load python/3.8.10
runtime_rc=$?
if [ "$runtime_rc" -ne 0 ]; then exit "$runtime_rc"; fi
set -u
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
umask 077
if [ "$#" -ne 6 ]; then echo "usage: sbatch wrapper BATCH REVIEW01 ... REVIEW05" >&2; exit 2; fi
BATCH_NUMBER="$1"; shift
if [ "$BATCH_NUMBER" -lt 5 ]; then echo "BATCH_NUMBER must be >=5" >&2; exit 2; fi
ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
C="$ROOT/private/continuation"; FORMAL=/work/home/lilysharp/private/formal800_20261012; COV=/work/home/lilysharp/private/production_coverage_20261017
BATCH=$(printf '%03d' "$BATCH_NUMBER"); OUT="$C/prepared/batch$BATCH"; CODE="$C/code/finalize_continuation.py"
mkdir -p "$OUT/validator_packets" "$OUT/validated" "$OUT/final" "$C/receipts" "$C/public" "$C/logs"
if [ "$BATCH_NUMBER" -eq 5 ]; then PRIOR="$ROOT/private/batch002_004/batch004/final"; PRIOR_RECEIPT="$ROOT/receipts/BATCH004_FINALIZE_RECEIPT.json"; else PREV=$(printf '%03d' $((BATCH_NUMBER-1))); PRIOR="$C/prepared/batch$PREV/final"; PRIOR_RECEIPT="$C/receipts/BATCH${PREV}_FINALIZE_RECEIPT.json"; fi
reviews=("$@"); validated=(); receipts=(); failed=0; total_records=0
for n in 01 02 03 04 05; do
 packet="$OUT/packets/PACKET_${n}_PRIVATE.jsonl"; core="$OUT/validator_packets/CORE_PACKET_${n}_PRIVATE.jsonl"; valid="$OUT/validated/VALIDATED_PACKET_${n}_PRIVATE.jsonl"; errors="$OUT/validated/VALIDATION_ERRORS_PACKET_${n}_PRIVATE.jsonl"; receipt="$C/receipts/BATCH${BATCH}_VALIDATION_RECEIPT_PACKET_${n}.json"
 packet_records=$(wc -l < "$packet"); total_records=$((total_records+packet_records))
 python3 "$CODE" core-packet --batch-number "$BATCH_NUMBER" --enriched-packet "$packet" --output "$core" --expected-records "$packet_records" || failed=1
 index=$((10#$n-1)); python3 "$FORMAL/code/validate_reviews.py" --packet "$core" --reviews "${reviews[$index]}" --schema "$FORMAL/code/FORMAL800_REVIEW_SCHEMA.json" --private-validated "$valid" --private-errors "$errors" --public-receipt "$receipt" --expected-records "$packet_records"
 validator_rc=$?
 if [ "$validator_rc" -ne 0 ] || [ ! -f "$receipt" ] || [ -s "$errors" ]; then printf 'validation_failed packet=%s rc=%s errors=%s\n' "$n" "$validator_rc" "$errors" >&2; failed=1; fi
 validated+=("$valid"); receipts+=("$receipt")
done
if [ "$failed" -ne 0 ]; then exit 2; fi
all="$OUT/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl"; all_packets="$OUT/packets/PACKETS_ALL100_PRIVATE.jsonl"; : > "$all"; : > "$all_packets"
for i in "${!validated[@]}"; do n=$(printf '%02d' $((i+1))); cat "${validated[$i]}" >> "$all"; cat "$OUT/packets/PACKET_${n}_PRIVATE.jsonl" >> "$all_packets"; done
python3 "$CODE" finalize --batch-number "$BATCH_NUMBER" --expected-records "$total_records" --enriched-packet "$all_packets" --validated-reviews "$all" --validation-receipts "${receipts[@]}" --validated-packets "${validated[@]}" --coverage-module "$COV/code/reconcile_coverage.py" --prior-receipt "$PRIOR_RECEIPT" --existing-ledger "$PRIOR/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" --existing-queue "$PRIOR/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" --existing-uncertainty "$PRIOR/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" --isolation-register "$C/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl" --private-ledger "$OUT/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" --private-queue "$OUT/final/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" --private-uncertainty "$OUT/final/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl" --public-counts "$C/public/BATCH${BATCH}_RESULTS_PUBLIC.json" --receipt "$C/receipts/BATCH${BATCH}_FINALIZE_RECEIPT.json"
