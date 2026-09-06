#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=02:00:00
#$ -pe omp 2
#$ -j y
#$ -N yax_r3_data

set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
AGENT_ROOT="$COMPUTE_ROOT/agents/data_audit"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
PYTHON_BIN="${YAX_PYTHON_BIN:-python3}"

mkdir -p "$AGENT_ROOT/results"
cd "$REPO_ROOT"
if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi

"$PYTHON_BIN" "$AGENT_ROOT/run_data_audit.py" \
  --repo-root "$REPO_ROOT" \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --contracts "$COMPUTE_ROOT/agents/rebuilt_baseline/results/NATIVE_TREATMENT_CONTRACTS.csv" \
  --universe "$COMPUTE_ROOT/agents/rebuilt_baseline/results/REBUILT_ELIGIBLE_UNIVERSE.csv" \
  --route-receipt "$COMPUTE_ROOT/agents/rebuilt_baseline/results/ROUTE_CONSERVATION_RECEIPT.json" \
  --output-dir "$AGENT_ROOT/results"

"$PYTHON_BIN" "$AGENT_ROOT/selfcheck.py" --output-dir "$AGENT_ROOT/results"
