#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -l h_rt=04:00:00
#$ -l mem_per_core=4G

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 OUTPUT"
  exit 2
fi

OUTPUT="$1"
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
PRIVATE_ROOT=/projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1

# No --benchmark is intentional: the 2026-08-28 alignment audit found no
# published benchmark on the exact signed-off Test C estimand. This run still
# measures paired precision and MDE_Delta,80 while leaving equivalence fields
# null and the freeze gate blocked.
"$PYTHON" yax/power/paired_equivalence_power.py \
  --cells "$PRIVATE_ROOT/young_relative_employment_cells_v1.csv" \
  --cells-receipt "$PRIVATE_ROOT/young_relative_employment_cells_v1_receipt.json" \
  --lookup yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv \
  --lookup-receipt yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP_RECEIPT.json \
  --computerization yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv \
  --computerization-receipt yax/measurement/COMPUTERIZATION_MEASURES_RECEIPT.json \
  --repetitions 999 \
  --seed 20260828 \
  --output "$OUTPUT"
