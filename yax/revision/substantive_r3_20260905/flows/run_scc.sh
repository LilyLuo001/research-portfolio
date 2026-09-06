#!/usr/bin/env bash
#$ -cwd
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_per_core=16G
#$ -pe omp 2
#$ -N yax_r3_flows

set -euo pipefail

PROJECT_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
REPO_ROOT=${REPO_ROOT:-$PROJECT_ROOT/repo_git2}
FLOW_ROOT=$PROJECT_ROOT/agents/flows
PRIVATE_SOURCE="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
PYTHON="${YAX_PYTHON_BIN:-python3}"
: "${WEIGHT_PATCH:?Pass the private corrected IPUMS weight-patch CSV.GZ as WEIGHT_PATCH}"

mkdir -p "$FLOW_ROOT/results"
cd "$REPO_ROOT"

"$PYTHON" yax/revision/substantive_r3_20260905/flows/run_flows_outcomes.py \
  --microdata "$PRIVATE_SOURCE/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_SOURCE/yax_referee_march_repair/cps_00011.csv.gz" \
  --weight-patch "$WEIGHT_PATCH" \
  --membership yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --analysis-spec yax/revision/substantive_r3_20260905/flows/ANALYSIS_SPEC_BEFORE_RESULTS.md \
  --output-dir "$FLOW_ROOT/results"

"$PYTHON" yax/revision/substantive_r3_20260905/flows/selfcheck.py \
  --results "$FLOW_ROOT/results"

