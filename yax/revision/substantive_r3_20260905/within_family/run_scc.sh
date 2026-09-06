#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=10:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_family
set -euo pipefail

PROJECT_ROOT="${YAX_SCC_PROJECT_ROOT:?Set YAX_SCC_PROJECT_ROOT to a writable compute root}"
PRIVATE_ROOT="${YAX_PRIVATE_ROOT:?Set YAX_PRIVATE_ROOT to the restricted input root}"
REPO="${YAX_REPO_ROOT:-$PROJECT_ROOT/repo_git2}"
OUT="${OUTPUT_ROOT:-$PROJECT_ROOT/outputs/within_family}"
PYTHON="${YAX_PYTHON_BIN:-python3}"
mkdir -p "$OUT"
cd "$REPO"

if [[ -n "${YAX_LEGACY_PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$YAX_LEGACY_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

"$PYTHON" yax/revision/substantive_r3_20260905/within_family/run_within_family.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --output-dir "$OUT" \
  --draws 9999

"$PYTHON" yax/revision/substantive_r3_20260905/within_family/selfcheck.py \
  --output-dir "$OUT"
