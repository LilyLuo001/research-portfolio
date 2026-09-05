#!/usr/bin/env bash
set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python
OUTPUT_DIR="$COMPUTE_ROOT/results/march_replacement_audit"

cd "$REPO_ROOT"
mkdir -p "$OUTPUT_DIR"

"$PYTHON_BIN" yax/revision/substantive_r3_20260905/survey_sim/run_march_replacement_audit.py \
  --wide "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --wide-request "$PRIVATE_ROOT/ai_telework_2017_2026/ipums_ai_telework_extract_superseding_submitted.json" \
  --repair-request "$PRIVATE_ROOT/yax_referee_march_repair/request.json" \
  --wide-ddi "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.xml" \
  --repair-ddi "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.xml" \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --cell-builder yax/revision/referee_20260905/run_referee_cells.py \
  --output-dir "$OUTPUT_DIR"

"$PYTHON_BIN" yax/revision/substantive_r3_20260905/survey_sim/selfcheck_march_replacement.py \
  --results "$OUTPUT_DIR"
