#!/bin/bash
set -euo pipefail
BU_ROOT=/projectnb/econdept/qluo/linkup_cpu_qualification_20261008_bu
test -f "${BU_ROOT}/INPUT_TRANSPORT_COMPLETE"
mkdir -p "${BU_ROOT}/logs" "${BU_ROOT}/control"
chmod 700 "${BU_ROOT}" "${BU_ROOT}/logs" "${BU_ROOT}/control"
C=${BU_ROOT}/control; CODE=${BU_ROOT}/bundle/code
get_or_submit(){
 local file=$1; shift
 if [ -s "${C}/${file}" ]; then cat "${C}/${file}"; return; fi
 local id; id=$("$@"); printf '%s\n' "${id}" > "${C}/${file}.tmp"; mv "${C}/${file}.tmp" "${C}/${file}"; printf '%s\n' "${id}"
}
P=$(get_or_submit PREP_JOB_ID qsub -terse -P econdept -q econ -l no_gpu=TRUE,h_rt=00:25:00,mem_per_core=2G -o "${BU_ROOT}/logs" -e "${BU_ROOT}/logs" -v BU_ROOT="${BU_ROOT}" "${CODE}/prepare_bu_sge.sh")
A=$(get_or_submit ARRAY_JOB_ID qsub -terse -P econdept -q econ -pe omp 8 -l no_gpu=TRUE,h_rt=00:20:00,mem_per_core=2G -t 1-32 -tc 4 -hold_jid "${P}" -o "${BU_ROOT}/logs" -e "${BU_ROOT}/logs" -v BU_ROOT="${BU_ROOT}" "${CODE}/run_fixed32_cpu_sge.sh")
F=$(get_or_submit FINAL_JOB_ID qsub -terse -P econdept -q econ -l no_gpu=TRUE,h_rt=00:15:00,mem_per_core=2G -hold_jid "${A}" -o "${BU_ROOT}/logs" -e "${BU_ROOT}/logs" -v BU_ROOT="${BU_ROOT}" "${CODE}/finalize_bu_sge.sh")
export P A F
python3 - "${C}/SUBMISSION_RECEIPT.json.tmp" <<'PY'
import json,os,sys
json.dump({'schema_version':'linkup-bu-sge-submission-v1','project':'econdept','queue':'econ','prep_job_id':os.environ['P'],'array_job_id':os.environ['A'],'array_range':'1-32','array_concurrency':4,'slots_per_task':8,'finalizer_job_id':os.environ['F'],'accelerator_requested':False},open(sys.argv[1],'w'),indent=2,sort_keys=True)
PY
mv "${C}/SUBMISSION_RECEIPT.json.tmp" "${C}/SUBMISSION_RECEIPT.json"; cat "${C}/SUBMISSION_RECEIPT.json"
