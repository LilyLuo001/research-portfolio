#!/usr/bin/env bash
set -euo pipefail

REPO=/projectnb/econdept/qluo/yax-referee-revision-20260905
PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python
OUT="$REPO/yax/revision/referee_round2_20260905/mobility_major/results"

cd "$REPO"
export PYTHONPATH=/usr3/graduate/qluo/.local/lib/python3.6/site-packages
mkdir -p "$OUT"

"$PYTHON" yax/revision/referee_round2_20260905/mobility_major/run_mobility_major.py \
  --microdata /projectnb/econdept/qluo/dax-private/ipums/ai_telework_2017_2026/cps_00009.csv.gz \
  --weight-patch /projectnb/econdept/qluo/dax-private/ipums/yax_phase2_weight_patch/cps_00010.csv.gz \
  --output-dir "$OUT"
