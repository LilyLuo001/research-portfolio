#!/bin/bash
#SBATCH --job-name=formal800_finish
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/finish-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/finish-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077
W=/work/home/lilysharp/private/formal800_20261012
C=$W/code
P=$W/private/validation/full_primary
A=$W/private/validation/full_audit
R=$W/private/validation/root
M=$W/private/audit_merge
F=$W/private/validation/final
SCHEMA=$C/FORMAL800_REVIEW_SCHEMA.json
merge_args=(--primary-validated "$P/validated_reviews.jsonl" --primary-receipt "$P/validation_receipt.json"
 --audit-validated "$A/validated_reviews.jsonl" --audit-receipt "$A/validation_receipt.json"
 --audit-packet "$W/private/freeze/BLIND_AUDIT_PACKET_PRIVATE.jsonl" --output-dir "$M")
case "${1:-}" in
 prepare-root)
  python3 "$C/run_review_validation.py" --assignments "$W/private/assignments/PRIMARY_ALL_ASSIGNMENTS.jsonl" \
   --packet-dir "$W/private/freeze" --review-dir "$W/private/reviews" --schema "$SCHEMA" --output-dir "$P"
  python3 "$C/run_review_validation.py" --assignments "$W/private/assignments/AUDIT_ALL_ASSIGNMENTS.jsonl" \
   --packet-dir "$W/private/validation" --review-dir "$W/private/reviews" --schema "$SCHEMA" --output-dir "$A"
  python3 "$C/merge_formal800_audit.py" "${merge_args[@]}"
  ;;
 validate-root)
  ROOT_N=$(python3 - "$M/ROOT_REVIEW_PACKET.jsonl" <<'PY'
import sys
from pathlib import Path
n=sum(bool(x.strip()) for x in Path(sys.argv[1]).read_text().splitlines())
if not 1 <= n <= 40:
    raise RuntimeError('root packet violates bounded adjudication contract')
print(n)
PY
  )
  python3 "$C/validate_reviews.py" --packet "$M/ROOT_REVIEW_PACKET.jsonl" \
   --reviews "$W/private/reviews/ROOT_RESOLUTIONS_PRIVATE.jsonl" --schema "$SCHEMA" \
   --private-validated "$R/validated_reviews.jsonl" --private-errors "$R/validation_errors.jsonl" \
   --public-receipt "$R/validation_receipt.json" --expected-records "$ROOT_N"
  ;;
 finalize)
  python3 "$C/merge_formal800_audit.py" "${merge_args[@]}" \
   --root-resolutions "$R/validated_reviews.jsonl" --resolution-receipt "$R/validation_receipt.json"
  python3 - "$P/BOUND_PACKET_PRIVATE.jsonl" "$R/validated_reviews.jsonl" "$F/FINAL_BOUND_PACKET_PRIVATE.jsonl" <<'PY'
import json, sys
from pathlib import Path
packet=[json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines() if x.strip()]
root={r['record_id']:r for r in (json.loads(x) for x in Path(sys.argv[2]).read_text().splitlines() if x.strip())}
if len(packet)!=719 or not 1 <= len(root) <= 40:
    raise RuntimeError('release differs from frozen719 contexts or maximum40 adjudications')
for row in packet:
    assignment=dict(row['assignment'])
    if row['record_id'] in root:
        if row['context_sha256']!=root[row['record_id']]['context_sha256']:
            raise RuntimeError('root source binding mismatch')
        assignment['provenance']='GPT-6/root; bounded Pro adjudication; exact context binding'
    else:
        assignment['provenance']+='; final frozen blind-conflict masking; originals retained'
    row['assignment']=assignment
out=Path(sys.argv[3]);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in packet))
PY
  python3 "$C/validate_reviews.py" --packet "$F/FINAL_BOUND_PACKET_PRIVATE.jsonl" \
   --reviews "$M/FINAL_REVIEW_RAW_PRIVATE.jsonl" --schema "$SCHEMA" \
   --private-validated "$F/validated_reviews.jsonl" --private-errors "$F/validation_errors.jsonl" \
   --public-receipt "$F/validation_receipt.json" --expected-records 719
  python3 "$C/analyze_formal800.py" --validated-reviews "$F/validated_reviews.jsonl" \
   --validation-receipt "$F/validation_receipt.json" --sampled-ad-map "$W/private/freeze/HIDDEN_LINKAGE_PRIVATE.jsonl" \
   --output-dir "$W/public/results" --private-ad-output "$W/private/final/AD_LEVEL_MEASURES.parquet" \
   --old-t1-reference prior/T1_coverage_funnel.csv \
   --old-t4-reference prior/T4_time_and_annual_diagnostics.csv
  ;;
 figures)
  python3 "$C/render_comparison_figures.py" --results-dir "$W/public/results" --output-dir "$W/public/results/figures"
  ;;
 *) echo 'Expected prepare-root, validate-root, finalize, or figures' >&2; exit 2;;
esac
