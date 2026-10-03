#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=${ROOT}/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json
RECEIPTS=${ROOT}/private/gate_v2_20261003/published_receipts_v2
RECEIPT=${ROOT}/state/FULL_FIRST_WAVE_SUBMISSION.json
CUTOFF_EPOCH=1791367200  # 2026-10-07 18:00:00 Asia/Shanghai
remove_own_cron() {
  local tmp
  tmp=$(mktemp "${ROOT}/state/linkup-crontab.XXXXXX")
  if /usr/bin/crontab -l >"${tmp}" 2>/dev/null; then
    /usr/bin/awk 'index($0,"LINKUP_FULL_FIRST_WAVE_TRIGGER")==0' "${tmp}" | /usr/bin/crontab -
  fi
  /usr/bin/rm -f "${tmp}"
}
exec 9>"${ROOT}/state/full-first-wave-trigger.lock"
/usr/bin/flock -n 9 || exit 0
test ! -f "${RECEIPT}" || exit 0
if (( $(date +%s) >= CUTOFF_EPOCH )); then
  /usr/local/python3.12/bin/python3 - "${ROOT}/state/FULL_FIRST_WAVE_TRIGGER_EXPIRED.json" <<'PY'
import json,os,sys,time
p=sys.argv[1]; t=p+'.tmp'
open(t,'w').write(json.dumps({'status':'expired_without_submission','cutoff_epoch':1791367200,
 'observed_at_epoch':time.time()},indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
  remove_own_cron
  exit 0
fi
shopt -s nullglob
receipts=("${RECEIPTS}"/*.published.json)
if ! test -f "${GATE}" || (( ${#receipts[@]} != 2464 )); then exit 0; fi
/usr/local/python3.12/bin/python3 "${ROOT}/code/prepare_full_hz_manifest.py" \
  --plans "${ROOT}/private/gate_v2_20261003/plans/kunshan.plan.jsonl" "${ROOT}/private/gate_v2_20261003/plans/wuzhen.plan.jsonl" \
  --sink /public/home/lilysharp/linkup_release_v1/full_semantic_v1 --receipts "${RECEIPTS}" \
  --output "${ROOT}/private/full_manifest_v2.jsonl"
job_id=$(cd "${ROOT}" && /opt/gridview/slurm/bin/sbatch --parsable code/run_full_first_wave_hz.sbatch)
/usr/local/python3.12/bin/python3 - "${RECEIPT}" "${job_id}" <<'PY'
import json,os,sys,time
p,j=sys.argv[1:]; t=p+'.tmp'
open(t,'w').write(json.dumps({'status':'submitted','job_id':j,'submitted_at_epoch':time.time(),
 'gate':'gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json','published_receipts':2464,
 'manifest':'full_manifest_v2.jsonl'},indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
remove_own_cron
