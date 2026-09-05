#!/usr/bin/env bash
#$ -cwd
#$ -j y
#$ -l h_rt=04:00:00
#$ -l mem_per_core=16G
#$ -pe omp 2
#$ -N yax_r3_flow_clusters

set -euo pipefail

PROJECT_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT=${REPO_ROOT:-$PROJECT_ROOT/repo_git2}
FLOW_ROOT=$PROJECT_ROOT/agents/flows
PRIVATE_SOURCE=/projectnb/econdept/qluo/dax-private/ipums
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
: "${WEIGHT_PATCH:?Pass the private corrected IPUMS weight-patch CSV.GZ as WEIGHT_PATCH}"

mkdir -p "$FLOW_ROOT/results_household"
cd "$REPO_ROOT"

"$PYTHON" yax/revision/substantive_r3_20260905/flows/run_link_cluster_sensitivity.py \
  --microdata "$PRIVATE_SOURCE/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_SOURCE/yax_referee_march_repair/cps_00011.csv.gz" \
  --weight-patch "$WEIGHT_PATCH" \
  --membership yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv \
  --bridge yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv \
  --fixed-results "$FLOW_ROOT/results/FLOW_AND_WORKER_OUTCOME_RESULTS.csv" \
  --fixed-influence "$FLOW_ROOT/results/TARGET_OCCUPATION_INFLUENCE.csv" \
  --amendment yax/revision/substantive_r3_20260905/flows/HOUSEHOLD_CLUSTER_AMENDMENT_BEFORE_RESULTS.md \
  --output-dir "$FLOW_ROOT/results_household"

"$PYTHON" yax/revision/substantive_r3_20260905/flows/selfcheck_link_cluster_sensitivity.py \
  --results "$FLOW_ROOT/results_household"

