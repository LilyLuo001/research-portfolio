#!/bin/bash -l
#$ -P econdept
#$ -N yax_r3_base
#$ -j y
#$ -l h_rt=12:00:00
#$ -l mem_per_core=8G
#$ -pe omp 4
#$ -o /project/econdept/qluo/yax-substantive-revision-20260905/logs/baseline_reproduction.log

set -euo pipefail

COMPUTE_ROOT=/project/econdept/qluo/yax-substantive-revision-20260905
REPO_ROOT="$COMPUTE_ROOT/repo_git2"
PYTHON_BIN=/usr3/graduate/qluo/portfolio/.venv/bin/python
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums
OUTPUT_ROOT="$COMPUTE_ROOT/results/baseline_reproduction"

mkdir -p "$OUTPUT_ROOT"
cd "$REPO_ROOT"

export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
export OMP_NUM_THREADS="${NSLOTS:-1}"
export OPENBLAS_NUM_THREADS="${NSLOTS:-1}"
export MKL_NUM_THREADS="${NSLOTS:-1}"

"$PYTHON_BIN" \
  yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py \
  --microdata "$PRIVATE_ROOT/ai_telework_2017_2026/cps_00009.csv.gz" \
  --repair-microdata "$PRIVATE_ROOT/yax_referee_march_repair/cps_00011.csv.gz" \
  --preperiod-cells "$PRIVATE_ROOT/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv" \
  --output-dir "$OUTPUT_ROOT"
