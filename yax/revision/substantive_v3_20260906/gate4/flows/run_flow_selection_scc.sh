#!/usr/bin/env bash
#$ -cwd
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_per_core=24G
#$ -pe omp 2
#$ -N yax_v3_flows

set -euo pipefail

: "${REPO_ROOT:?Set REPO_ROOT to the clean SCC worktree}"
: "${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the authorized restricted input root}"
: "${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to the project compute root}"
: "${OUTPUT_DIR:?Set OUTPUT_DIR to a fresh aggregate-only output directory}"
PYTHON=${YAX_PYTHON_BIN:-python3}

cd "$REPO_ROOT"
test ! -e "$OUTPUT_DIR"

"$PYTHON" yax/revision/substantive_v3_20260906/gate4/flows/run_flow_selection.py \
  --microdata "$YAX_PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$YAX_PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --weight-patch "$YAX_SCC_PROJECT_ROOT/private/ipums/yax_r3_flow_weight_patch/cps_00012.csv.gz" \
  --membership yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv \
  --legacy-membership yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --legacy-flow-results yax/revision/substantive_r3_20260905/flows/results/FLOW_AND_WORKER_OUTCOME_RESULTS.csv \
  --legacy-household-results yax/revision/substantive_r3_20260905/flows/results_household/PERSON_HOUSEHOLD_CLUSTER_SENSITIVITY.csv \
  --output-dir "$OUTPUT_DIR"

"$PYTHON" yax/revision/substantive_v3_20260906/gate4/flows/validate_flow_selection_outputs.py \
  "$OUTPUT_DIR" | tee "$OUTPUT_DIR/VALIDATION_REPORT.json"
