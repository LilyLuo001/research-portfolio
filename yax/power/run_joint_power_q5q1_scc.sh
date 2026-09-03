#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -l h_rt=02:00:00
#$ -l mem_per_core=4G

set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 AI_MEASURE COMPUTERIZATION_MEASURE OUTPUT"
  exit 2
fi

AI_MEASURE="$1"
COMPUTERIZATION_MEASURE="$2"
OUTPUT="$3"
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1

"$PYTHON" yax/power/joint_computerization_power.py \
  --cells "$PRIVATE_ROOT/young_relative_employment_cells_v1.csv" \
  --cells-receipt "$PRIVATE_ROOT/young_relative_employment_cells_v1_receipt.json" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --lookup-receipt yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --computerization-receipt yax/measurement/COMPUTERIZATION_MEASURES_RECEIPT.json \
  --ai-measure "$AI_MEASURE" \
  --computerization-measure "$COMPUTERIZATION_MEASURE" \
  --beta-c -0.05129329438755058 \
  --effect-scale q5_q1 \
  --repetitions 999 \
  --bootstrap-draws 999 \
  --mde-bootstrap-draws 999 \
  --seed 20260829 \
  --output "$OUTPUT"
