#!/usr/bin/env bash
set -euo pipefail

cd /projectnb/econdept/qluo/yax-referee-revision-20260905
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages

/usr3/graduate/qluo/portfolio/.venv/bin/python \
  yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py \
  --microdata /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz \
  --repair-microdata /projectnb/econdept/qluo/dax-private/ipums/yax_referee_march_repair/cps_00011.csv.gz \
  --preperiod-cells /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir yax/revision/referee_round2_20260905/composition_influence/results
