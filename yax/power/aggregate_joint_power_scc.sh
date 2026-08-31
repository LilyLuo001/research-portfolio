#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -l h_rt=00:15:00
#$ -l mem_per_core=2G

set -euo pipefail

PYTHON=/usr3/graduate/qluo/portfolio/.venv/bin/python

"$PYTHON" yax/power/aggregate_joint_power.py \
  yax/power/scenarios_v2/beta_onet_primary.json \
  yax/power/scenarios_v2/beta_webb_primary.json \
  yax/power/scenarios_v2/alpha_onet_primary.json \
  yax/power/scenarios_v2/alpha_webb_primary.json \
  --output yax/power/JOINT_POWER_AGGREGATE_v2.json \
  --markdown yax/power/POWER_NOTE_v2.md

