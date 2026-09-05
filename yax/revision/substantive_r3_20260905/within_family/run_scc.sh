#!/bin/bash -l
#$ -P econdept
#$ -l h_rt=10:00:00
#$ -l mem_per_core=16G
#$ -pe omp 1
#$ -j y
#$ -N yax_r3_family
#$ -o /project/econdept/qluo/yax-substantive-revision-20260905/logs/within_family.log
set -euo pipefail

REPO=/project/econdept/qluo/yax-substantive-revision-20260905/repo_git2
OUT=/project/econdept/qluo/yax-substantive-revision-20260905/outputs/within_family
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
mkdir -p "$OUT"
cd "$REPO"

export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

"$PYTHON" yax/revision/substantive_r3_20260905/within_family/run_within_family.py \
  --microdata /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz \
  --repair-microdata /projectnb/econdept/qluo/dax-private/ipums/yax_referee_march_repair/cps_00011.csv.gz \
  --preperiod-cells /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir "$OUT" \
  --draws 9999

"$PYTHON" yax/revision/substantive_r3_20260905/within_family/selfcheck.py \
  --output-dir "$OUT"

