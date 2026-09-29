#!/bin/bash
set -euo pipefail

MODE=${MODE:-backup}
ROOT=/public/home/lilysharp/linkup_analysis_v1
RELEASE=${ROOT}/stage_c_release_v1
STATE=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan
PY=/public/software/apps/python/3.8.10/bin/python3
export PYTHONPATH=${ROOT}/stage_b/runtime_py38

resume_parent() {
  if test "${MODE}" = inplace && test -n "${BATCH_PARENT_PID:-}"; then
    kill -CONT "${BATCH_PARENT_PID}" 2>/dev/null || true
  fi
}

success=0
cleanup() {
  rc=$?
  if test "${success}" -eq 1 && test -n "${BACKUP_JOB_ID:-}"; then
    scancel "${BACKUP_JOB_ID}" 2>/dev/null || true
  fi
  resume_parent
  exit "${rc}"
}
trap cleanup EXIT INT TERM

if test "${MODE}" = inplace; then
  : "${BATCH_PARENT_PID:?missing BATCH_PARENT_PID}"
  test -r "/proc/${BATCH_PARENT_PID}/cmdline"
  tr '\0' ' ' < "/proc/${BATCH_PARENT_PID}/cmdline" | grep -q 'slurm_script'
  kill -STOP "${BATCH_PARENT_PID}"
  while pgrep -u "${USER}" -f 'regional_runner.py.*--partition-id part0' >/dev/null; do
    sleep 5
  done
fi

for required in prepare_shard_input.py regional_runner.py enrichment.py lean_writer.py; do
  test -r "${RELEASE}/${required}"
done

"${PY}" "${RELEASE}/regional_runner.py" \
  --transfer-mode queue --partition-id takeover_all --plan "${STATE}/plan.jsonl" \
  --buffer-root "${STATE}/buffer/part1" --checkpoint-root "${STATE}/checkpoints" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${RELEASE}/enrichment.py" --lean-writer "${RELEASE}/lean_writer.py" \
  --workers 32 --per-shard-output-cap-bytes 500000000 \
  --per-shard-buffer-reserve-bytes 1000000000 \
  --buffer-cap-bytes 2000000000 --free-reserve-bytes 8000000000

success=1
