#!/bin/bash
#SBATCH --job-name=linkup-semantic-ks-4way-handoff
#SBATCH --partition=kshctest02
#SBATCH --nodes=2
#SBATCH --ntasks=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan/logs/compute-4way-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan/logs/compute-4way-%j.err
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1
RELEASE=${ROOT}/stage_c_release_v1
STATE=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan
CONTROL=${STATE}/handoff_4way
mkdir -p "${CONTROL}" "${STATE}/logs"
exec 9>"${CONTROL}/handoff.lock"
flock -n 9 || { echo 'another 4-way handoff owns the lock' >&2; exit 75; }
export PYTHONPATH=${ROOT}/stage_b/runtime_py38
PY=/public/software/apps/python/3.8.10/bin/python3
timeout --signal=TERM 300s "${PY}" "${RELEASE}/ks_4way_handoff.py" \
  --full-plan "${STATE}/plan.jsonl" --checkpoint-root "${STATE}/checkpoints" \
  --output-root "${CONTROL}" --old-job-ids 123218160 123271262 --max-prepare-seconds 300
status=$("${PY}" -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${CONTROL}/KS_4WAY_HANDOFF.json")
test "${status}" != already_complete || exit 0

submit_nested() {
  index=$1; name=linkup-semantic-ks-split${index}-v1
  plan=${CONTROL}/plan.ks_split${index}.jsonl
  digest=$(sha256sum "${plan}" | awk '{print $1}')
  intent=${CONTROL}/split${index}.submission.intent.json
  receipt=${CONTROL}/split${index}.submission.json
  test ! -e "${receipt}" || return 0
  test ! -e "${intent}" || { echo "unresolved prior submission intent: split${index}" >&2; return 75; }
  "${PY}" - "${intent}" "${name}" <<'PY'
import json,os,sys,time
p,n=sys.argv[1:]; t=p+'.tmp'; open(t,'w').write(json.dumps({'status':'intent','job_name':n,'at':time.time()},sort_keys=True)+'\n'); os.replace(t,p)
PY
  out=${CONTROL}/split${index}.sbatch.stdout; err=${CONTROL}/split${index}.sbatch.stderr
  set +e
  env -u SBATCH_NODES -u SBATCH_NTASKS -u SBATCH_NTASKS_PER_NODE \
      -u SBATCH_CPUS_PER_TASK -u SBATCH_MEM_PER_NODE -u SBATCH_MEM_PER_CPU \
      -u SBATCH_GRES -u SBATCH_GRES_FLAGS -u SLURM_GRES_FLAGS \
    sbatch --parsable --job-name="${name}" --partition=kshctest02 --time=2-00:00:00 \
      --nodes=1 --ntasks=1 --ntasks-per-node=1 \
      --cpus-per-task=32 --mem=96G --export=ALL,PARTITION_ID="ks_split${index}",PLAN="${plan}",EXPECTED_PLAN_SHA256="${digest}" \
      "${RELEASE}/run_ks_split_worker.sbatch" >"${out}" 2>"${err}"
  rc=$?; set -e
  job=$(head -1 "${out}" | cut -d';' -f1 | tr -d '[:space:]')
  test "${rc}" -eq 0 && printf %s "${job}" | grep -Eq '^[0-9]+$' || return 75
  "${PY}" - "${receipt}" "${job}" "${name}" "${digest}" <<'PY'
import json,os,sys,time
p,j,n,d=sys.argv[1:]; t=p+'.tmp'; open(t,'w').write(json.dumps({'status':'submitted','job_id':j,'job_name':n,'plan_sha256':d,'at':time.time()},sort_keys=True)+'\n'); os.replace(t,p)
PY
}

run_local() {
  index=$1; plan=${CONTROL}/plan.ks_split${index}.jsonl
  digest=$(sha256sum "${plan}" | awk '{print $1}')
  srun --exclusive --nodes=1 --ntasks=1 --ntasks-per-node=1 --cpus-per-task=32 \
    --export=ALL,PARTITION_ID="ks_split${index}",PLAN="${plan}",EXPECTED_PLAN_SHA256="${digest}" \
    bash "${RELEASE}/run_ks_split_worker.sbatch"
}
run_local 0 & p0=$!
run_local 1 & p1=$!
nested_rc=0
submit_nested 2 || nested_rc=$?
submit_nested 3 || nested_rc=$?
set +e
wait "${p0}"; r0=$?
wait "${p1}"; r1=$?
set -e
test "${nested_rc}" -eq 0 && test "${r0}" -eq 0 && test "${r1}" -eq 0
