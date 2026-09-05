#!/usr/bin/env bash
set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python
OUTPUT_DIR="$COMPUTE_ROOT/results/inf03_inf05"
HOUSEHOLD_DRAWS="${HOUSEHOLD_DRAWS:-199}"
SIMULATION_DRAWS="${SIMULATION_DRAWS:-199}"

cd "$REPO_ROOT"
mkdir -p "$OUTPUT_DIR"

"$PYTHON_BIN" yax/revision/substantive_r3_20260905/survey_sim/run_inf03_inf05.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --treatment-contract yax/revision/substantive_r3_20260905/rebuilt_baseline/results/NATIVE_TREATMENT_CONTRACTS.csv \
  --march-audit-receipt yax/revision/substantive_r3_20260905/survey_sim/results/march_replacement_audit/MARCH_REPLACEMENT_AUDIT_RECEIPT.json \
  --household-draws "$HOUSEHOLD_DRAWS" \
  --simulation-draws "$SIMULATION_DRAWS" \
  --output-dir "$OUTPUT_DIR"

"$PYTHON_BIN" yax/revision/substantive_r3_20260905/survey_sim/selfcheck_inf03_inf05.py \
  --results "$OUTPUT_DIR" \
  --household-draws "$HOUSEHOLD_DRAWS" \
  --simulation-draws "$SIMULATION_DRAWS"
