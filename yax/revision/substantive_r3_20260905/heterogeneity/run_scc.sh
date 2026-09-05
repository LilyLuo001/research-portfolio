#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_het
#$ -j y
#$ -l h_rt=08:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4
#$ -o /project/econdept/qluo/yax-substantive-revision-20260905/logs/heterogeneity_final.log

set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
AGENT_ROOT="$COMPUTE_ROOT/agents/heterogeneity"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python
OUTPUT_ROOT="$COMPUTE_ROOT/results/heterogeneity_final"

mkdir -p "$OUTPUT_ROOT" "$COMPUTE_ROOT/logs"
cd "$REPO_ROOT"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
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
