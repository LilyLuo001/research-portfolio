#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1
RELEASE=${ROOT}/stage_c_release_v1
STATE=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan
export PYTHONPATH=${ROOT}/stage_b/runtime_py38
exec /public/software/apps/python/3.8.10/bin/python3 "${RELEASE}/ks_4way_completion_controller.py" \
  --full-plan "${STATE}/plan.jsonl" --handoff-root "${STATE}/handoff_4way" \
  --checkpoint-root "${STATE}/checkpoints"
