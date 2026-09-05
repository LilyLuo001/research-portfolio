#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=02:00:00
#$ -pe omp 2
#$ -j y
#$ -N yax_r3_data

set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
AGENT_ROOT="$COMPUTE_ROOT/agents/data_audit"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python

mkdir -p "$AGENT_ROOT/results"
cd "$REPO_ROOT"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages

"$PYTHON_BIN" "$AGENT_ROOT/run_data_audit.py" \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --contracts "$COMPUTE_ROOT/agents/rebuilt_baseline/results/NATIVE_TREATMENT_CONTRACTS.csv" \
  --universe "$COMPUTE_ROOT/agents/rebuilt_baseline/results/REBUILT_ELIGIBLE_UNIVERSE.csv" \
  --route-receipt "$COMPUTE_ROOT/agents/rebuilt_baseline/results/ROUTE_CONSERVATION_RECEIPT.json" \
  --output-dir "$AGENT_ROOT/results"

"$PYTHON_BIN" "$AGENT_ROOT/selfcheck.py" --output-dir "$AGENT_ROOT/results"
