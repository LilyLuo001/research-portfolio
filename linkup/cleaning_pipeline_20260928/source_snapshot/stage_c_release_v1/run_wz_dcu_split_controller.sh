#!/bin/bash
set -euo pipefail
ROOT=/work/home/lilysharp/linkup_analysis_v1
RELEASE=${ROOT}/stage_c_release_v1
STATE=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
exec python3 "${RELEASE}/wz_dcu_split_controller.py" \
 --semantic-root "${STATE}" --release-root "${RELEASE}" \
 --full-plan "${STATE}/plan.jsonl" --new-plan "${STATE}/WZ_REMAINING_PLAN_PRIVATE.jsonl" \
 --completed-plan "${STATE}/plan.dcu_completed_before_split.jsonl" \
 --part0-plan "${STATE}/plan.dcu_part0.jsonl" --part1-plan "${STATE}/plan.dcu_part1.jsonl" \
 --old-code "${STATE}/WZ_OLD_CODE.json" --new-code "${STATE}/WZ_NEW_CODE.json" \
 --new-provenance "${STATE}/WZ_NEW_DCU_PROVENANCE.json"
