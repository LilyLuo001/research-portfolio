#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=${ROOT}/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json
MANIFEST=${ROOT}/private/full_manifest_v2.jsonl
RECEIPT=${ROOT}/state/SEMANTIC_NARROW_SUBMISSION.json
CUTOFF_EPOCH=1791367200
remove_own_cron() {
  local tmp
  tmp=$(mktemp "${ROOT}/state/narrow-crontab.XXXXXX")
  if /usr/bin/crontab -l >"${tmp}" 2>/dev/null; then
    /usr/bin/awk 'index($0,"LINKUP_SEMANTIC_NARROW_TRIGGER")==0' "${tmp}" | /usr/bin/crontab -
  fi
  /usr/bin/rm -f "${tmp}"
}
exec 9>"${ROOT}/state/semantic-narrow-trigger.lock"
/usr/bin/flock -n 9 || exit 0
test ! -f "${RECEIPT}" || { remove_own_cron; exit 0; }
if (( $(date +%s) >= CUTOFF_EPOCH )); then
  /usr/local/python3.12/bin/python3 - "${ROOT}/state/SEMANTIC_NARROW_TRIGGER_EXPIRED.json" <<'PY'
import json,os,sys,time
p=sys.argv[1]; t=p+'.tmp'; open(t,'w').write(json.dumps({'status':'expired_without_submission',
 'cutoff_epoch':1791367200,'observed_at_epoch':time.time()},indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
  remove_own_cron; exit 0
fi
test -f "${GATE}" || exit 0
test -f "${MANIFEST}" || exit 0
test "$(wc -l < "${MANIFEST}")" -eq 2464 || exit 0
job_id=$(cd "${ROOT}" && /opt/gridview/slurm/bin/sbatch --parsable code/pre_revelio_execution_v1/run_semantic_narrow_hz.sbatch)
/usr/local/python3.12/bin/python3 - "${RECEIPT}" "${job_id}" <<'PY'
import json,os,sys,time
p,j=sys.argv[1:]; t=p+'.tmp'; open(t,'w').write(json.dumps({'status':'submitted','job_id':j,
 'submitted_at_epoch':time.time(),'gate':'gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json','manifest_rows':2464,
 'manifest':'full_manifest_v2.jsonl'},
 indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
remove_own_cron
