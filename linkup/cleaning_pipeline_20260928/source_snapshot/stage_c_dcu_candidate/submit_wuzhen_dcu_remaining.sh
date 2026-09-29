#!/bin/bash
# Fail-closed submitter: login environments may export enforce-binding and
# override the reviewed disable-binding directive in the batch script.
set -euo pipefail

STATE=${STATE_ROOT:-/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen}
PLAN=${REMAINING_PLAN:-${STATE}/WZ_REMAINING_PLAN_PRIVATE.jsonl}
SCRIPT=${DCU_BATCH_SCRIPT:-/work/home/lilysharp/linkup_analysis_v1/stage_c_dcu_candidate/run_wuzhen_dcu_remaining.sbatch}
PY=/public/software/apps/python/3.8.10/bin/python3
RECEIPT=${STATE}/WZ_DCU_SUBMISSION.json
INTENT=${STATE}/WZ_DCU_SUBMISSION.intent.json

test -s "${PLAN}"
test -r "${SCRIPT}"
test ! -e "${RECEIPT}" || { cat "${RECEIPT}"; exit 0; }
active=$(squeue -h -u "${USER}" -n linkup-semantic-wz-dcu-r1 -o %A | head -1 || true)
test -z "${active}" || { echo "active job without canonical receipt: ${active}" >&2; exit 75; }

"${PY}" - "${INTENT}" "${SCRIPT}" "${PLAN}" <<'PY'
import json, os, sys, time
path, script, plan = sys.argv[1:]
temp = path + ".tmp"
open(temp, "w").write(json.dumps({
    "status": "intent", "created_at": time.time(), "script": script,
    "remaining_plan": plan,
    "submit_override": "remove inherited GRES flags; explicit disable-binding",
}, indent=2, sort_keys=True) + "\n")
os.replace(temp, path)
PY

stdout=${STATE}/wz-dcu-sbatch.stdout
stderr=${STATE}/wz-dcu-sbatch.stderr
set +e
env -u SBATCH_GRES_FLAGS -u SLURM_GRES_FLAGS \
  sbatch --parsable --gres-flags=disable-binding --cpus-per-task=32 --mem=96G \
  --export=ALL,REMAINING_PLAN="${PLAN}" "${SCRIPT}" >"${stdout}" 2>"${stderr}"
rc=$?
set -e
job=$(head -1 "${stdout}" | cut -d';' -f1 | tr -d '[:space:]')
if test "${rc}" -ne 0 || ! printf %s "${job}" | grep -Eq '^[0-9]+$'; then
  echo "sbatch rejected; inspect ${stdout} and ${stderr}" >&2
  exit 75
fi

"${PY}" - "${RECEIPT}" "${job}" "${SCRIPT}" "${PLAN}" "${rc}" "${stdout}" "${stderr}" <<'PY'
import hashlib, json, os, sys, time
path, job, script, plan, rc, stdout, stderr = sys.argv[1:]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
value = {
    "status": "submitted", "job_id": job,
    "job_name": "linkup-semantic-wz-dcu-r1", "partition": "wzhdtest",
    "requested_tres": {"dcu": 1, "cpu": 32, "mem": "96G"},
    "gres_flags": "disable-binding", "inherited_gres_flags_removed": True,
    "submitted_at": time.time(), "script": script, "script_sha256": sha(script),
    "remaining_plan": plan, "remaining_plan_sha256": sha(plan),
    "sbatch_returncode": int(rc), "sbatch_stdout": open(stdout).read(),
    "sbatch_stderr": open(stderr).read(),
}
temp = path + ".tmp"
open(temp, "w").write(json.dumps(value, indent=2, sort_keys=True) + "\n")
os.replace(temp, path)
PY
cat "${RECEIPT}"
