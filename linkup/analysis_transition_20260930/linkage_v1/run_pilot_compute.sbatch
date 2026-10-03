#!/bin/bash
#SBATCH --job-name=linkage_pilot_v1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=linkage_pilot_%j.log
set -euo pipefail

: "${LEAN_KEY_DIR:?set to staged key-only pilot directory}"
: "${RECORD_FILES:?set to comma-separated narrow Records files}"
: "${ONET_FILES:?set to comma-separated narrow O*NET files}"
: "${LINKAGE_ROOT:?set to deployed linkage_v1 directory}"
: "${OUTPUT_DIR:?set to private runtime output directory}"

export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
PY=/public/software/apps/python/3.8.10/bin/python3
IFS=, read -r -a record_args <<< "$RECORD_FILES"
IFS=, read -r -a onet_args <<< "$ONET_FILES"
"$PY" "$LINKAGE_ROOT/build_linkage_coverage.py" \
  --lean "$LEAN_KEY_DIR"/*.parquet \
  --records "${record_args[@]}" \
  --onet "${onet_args[@]}" \
  --official-codes "$LINKAGE_ROOT/official_onet2019_occupations.csv" \
  --rules "$LINKAGE_ROOT/RULES.json" \
  --output "$OUTPUT_DIR/PILOT_COVERAGE.json" --threads 4 --memory-limit 12GB \
  --records-lookup-scope complete_user_supplied --onet-lookup-scope complete
