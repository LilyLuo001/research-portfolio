#!/usr/bin/env bash
set -euo pipefail
cd /projectnb/econdept/qluo/yax-referee-revision-20260905
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
/usr3/graduate/qluo/portfolio/.venv/bin/python \
  yax/revision/referee_20260905/run_referee_core.py \
  --stage core \
  --microdata /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz \
  --preperiod-cells /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir /projectnb/econdept/qluo/yax-referee-revision-results-20260905/core
