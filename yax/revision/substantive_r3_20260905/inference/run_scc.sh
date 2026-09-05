#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_dep
#$ -j y
#$ -l h_rt=12:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4

set -euo pipefail

COMPUTE_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PYTHON_BIN="${YAX_PYTHON_BIN:-python3}"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
OUTPUT_ROOT="$COMPUTE_ROOT/results/dependence_audit"

mkdir -p "$OUTPUT_ROOT"
cd "$REPO_ROOT"

if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/inference/run_dependence_audit.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --output-dir "$OUTPUT_ROOT"

"$PYTHON_BIN" \
  yax/revision/substantive_r3_20260905/inference/selfcheck.py \
  --results-dir "$OUTPUT_ROOT"
