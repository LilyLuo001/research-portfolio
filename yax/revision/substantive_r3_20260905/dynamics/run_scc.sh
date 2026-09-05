#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=12:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_dynamics
#$ -o /project/econdept/qluo/yax-substantive-revision-20260905/agents/dynamics/scc_execution.log
set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO="$COMPUTE_ROOT/repo_git2"
AGENT="$COMPUTE_ROOT/agents/dynamics"
OUT="$AGENT/results"
PRIVATE=/projectnb/econdept/qluo/dax-private/ipums
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
REBUILT="$COMPUTE_ROOT/agents/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv"

mkdir -p "$OUT"
cd "$REPO"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
export YAX_REPO_ROOT="$REPO"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

REBUILT_ARGS=()
if [ -f "$REBUILT" ]; then
  REBUILT_ARGS=(--rebuilt-membership "$REBUILT")
fi

"$PYTHON" "$AGENT/run_dynamics.py" \
  --microdata "$PRIVATE/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --output-dir "$OUT" \
  "${REBUILT_ARGS[@]}"

"$PYTHON" "$AGENT/selfcheck.py" --output-dir "$OUT"
