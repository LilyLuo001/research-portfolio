#!/bin/bash
#SBATCH --job-name=formal800_primary_vs_final
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/primary-vs-final-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/primary-vs-final-%j.err
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
BASE=$W/public/primary_baseline
FINAL=$W/public/results
SUMMARY=$W/public/primary_vs_final

run_baseline() {
  rm -f "$BASE/ANALYSIS_RECEIPT.json"
  python3 "$C/analyze_formal800.py" \
   --validated-reviews "$P/validated_reviews.jsonl" \
   --validation-receipt "$P/validation_receipt.json" \
   --sampled-ad-map "$W/private/freeze/HIDDEN_LINKAGE_PRIVATE.jsonl" \
   --output-dir "$BASE" \
   --private-ad-output "$W/private/primary_baseline/AD_LEVEL_MEASURES.parquet" \
   --old-t1-reference prior/T1_coverage_funnel.csv \
   --old-t4-reference prior/T4_time_and_annual_diagnostics.csv
}

run_summary() {
  rm -f "$SUMMARY/PRIMARY_VS_FINAL_RECEIPT.json"
  python3 "$C/summarize_primary_final.py" \
   --baseline-dir "$BASE" --final-dir "$FINAL" --output-dir "$SUMMARY"
}

case "${1:-all}" in
  baseline) run_baseline ;;
  summarize) run_summary ;;
  all) run_baseline; run_summary ;;
  *) echo 'Expected baseline, summarize, or all' >&2; exit 2 ;;
esac
