#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_het
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4

set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
AGENT_ROOT="$COMPUTE_ROOT/agents/heterogeneity"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
PYTHON_BIN="${YAX_PYTHON_BIN:-python3}"
OUTPUT_ROOT="$COMPUTE_ROOT/results/heterogeneity_final"

mkdir -p "$OUTPUT_ROOT" "$COMPUTE_ROOT/logs"
cd "$REPO_ROOT"
if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

"$PYTHON_BIN" "$AGENT_ROOT/run_heterogeneity.py" \
  --repo-root "$REPO_ROOT" \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --bridge "$REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --membership "$AGENT_ROOT/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --specification "$AGENT_ROOT/ANALYSIS_SPEC_BEFORE_RESULTS.md" \
  --output-dir "$OUTPUT_ROOT"

"$PYTHON_BIN" "$AGENT_ROOT/selfcheck.py" --results-dir "$OUTPUT_ROOT"
