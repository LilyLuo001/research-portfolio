#!/bin/bash -l
#$ -P econdept
#$ -N yax_r2_prec
#$ -l h_rt=08:00:00
#$ -l mem_per_core=16G
#$ -j y
#$ -o /projectnb/econdept/qluo/yax-referee-round2-results-20260905/precision_rotation/scc_execution.log

set -euo pipefail
cd /projectnb/econdept/qluo/yax-referee-revision-20260905

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
PY=/usr3/graduate/qluo/portfolio/.venv/bin/python
OUT=/projectnb/econdept/qluo/yax-referee-round2-results-20260905/precision_rotation

"$PY" yax/revision/referee_round2_20260905/precision_rotation/run_precision_rotation.py \
  --stage main \
  --microdata /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz \
  --repair-microdata /projectnb/econdept/qluo/dax-private/ipums/yax_referee_march_repair/cps_00011.csv.gz \
  --preperiod-cells /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir "$OUT"

"$PY" yax/revision/referee_round2_20260905/precision_rotation/run_precision_rotation.py \
  --stage simulation \
  --preperiod-cells /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir "$OUT"
