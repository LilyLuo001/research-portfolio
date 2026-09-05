#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=02:00:00
#$ -pe omp 4
#$ -j y
#$ -N yax_r3_base03

set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
AGENT_ROOT="$COMPUTE_ROOT/agents/rebuilt_baseline"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python

mkdir -p "$AGENT_ROOT/results"
cd "$REPO_ROOT"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages

"$PYTHON_BIN" "$AGENT_ROOT/run_rebuilt_corrected_baseline.py" \
  --repo-root "$REPO_ROOT" \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --historical-preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --lookup "$REPO_ROOT/yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv" \
  --computerization "$REPO_ROOT/yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv" \
  --rule-b-values "$REPO_ROOT/yax/measurement/RULE_B_VALUES_CENSUS2018.csv" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --first-access-receipt "$REPO_ROOT/yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json" \
  --output-dir "$AGENT_ROOT/results"

"$PYTHON_BIN" "$AGENT_ROOT/selfcheck.py" --output-dir "$AGENT_ROOT/results"
