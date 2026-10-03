#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=/public/home/lilysharp/linkup_release_v1/full_semantic_v1/ALL_REGIONS_VERIFIED_COMPLETE.json
RECEIPT=${ROOT}/state/FULL_FIRST_WAVE_SUBMISSION.json
exec 9>"${ROOT}/state/full-first-wave-trigger.lock"
/usr/bin/flock -n 9 || exit 0
test ! -f "${RECEIPT}" || exit 0
shopt -s nullglob
receipts=("${ROOT}"/private/published_receipts/*.published.json)
if ! test -f "${GATE}" || (( ${#receipts[@]} != 2464 )); then exit 0; fi
job_id=$(cd "${ROOT}" && /opt/gridview/slurm/bin/sbatch --parsable code/run_full_first_wave_hz.sbatch)
/usr/local/python3.12/bin/python3 - "${RECEIPT}" "${job_id}" <<'PY'
import json,os,sys,time
p,j=sys.argv[1:]; t=p+'.tmp'
open(t,'w').write(json.dumps({'status':'submitted','job_id':j,'submitted_at_epoch':time.time(),
 'gate':'ALL_REGIONS_VERIFIED_COMPLETE.json','published_receipts':2464},indent=2,sort_keys=True)+'\n'); os.replace(t,p)
PY
/usr/bin/crontab -l 2>/dev/null | grep -v 'LINKUP_FULL_FIRST_WAVE_TRIGGER' | /usr/bin/crontab - || true
