#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
CUTOFF_EPOCH=1791367200
remove_dispatcher() {
  local tmp
  tmp=$(mktemp "${ROOT}/state/p0p1-crontab.XXXXXX")
  if /usr/bin/crontab -l >"${tmp}" 2>/dev/null; then
    /usr/bin/awk 'index($0,"LINKUP_P0_P1_DISPATCHER")==0' "${tmp}" | /usr/bin/crontab -
  fi
  /usr/bin/rm -f "${tmp}"
}
exec 9>"${ROOT}/state/p0-p1-dispatcher.lock"
/usr/bin/flock -n 9 || exit 0
"${ROOT}/code/trigger_full_hz_once.sh"
"${ROOT}/code/pre_revelio_execution_v1/trigger_semantic_narrow_once.sh"
if { test -f "${ROOT}/state/FULL_FIRST_WAVE_SUBMISSION.json" &&
     test -f "${ROOT}/state/SEMANTIC_NARROW_SUBMISSION.json"; } ||
   (( $(date +%s) >= CUTOFF_EPOCH )); then
  remove_dispatcher
fi
