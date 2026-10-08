#!/bin/bash
# Queue-neutral fixed-32 CPU qualification. Supply --partition and optional array concurrency at submission.
#SBATCH --job-name=linkup-cpu-q32
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --partition=kshctest02
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --array=0-31%4

set -euo pipefail
umask 077
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10 >/dev/null 2>&1 || true
set -u

: "${SOURCE_JSONL:?path to the archived fixed-32 source JSONL}"
: "${RUN_ROOT:?new private output directory for this qualification}"
: "${BUNDLE:?transported immutable qualification bundle}"

RUNTIME=${RUNTIME:-/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/build-run-46032322/build/bin}
MODEL=${MODEL:-/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/staged_artifacts/Qwen3-8B-Q4_K_M.gguf}
ARCHIVE=${ARCHIVE:-/work/home/lilysharp/linkup_cloud_execution_20261008/run-20261008T053138Z/payload}
PROMPT=${PROMPT:-${ARCHIVE}/production_standard_20261008/EXTRACTION_PROMPT.md}
SCHEMA=${SCHEMA:-${ARCHIVE}/compact_measurement_20261007/schema/compact_model_output.schema.json}
export LD_LIBRARY_PATH="${RUNTIME}:${BUNDLE:-}/runtime/gcc11-lib64:${BUNDLE:-}/runtime/gcc11-lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
MODEL_SHA=d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785
RUNTIME_SHA=66c94c83f239a97c458e772295c9fc556ca8ea743dbb7c704e20ffb758bd533a
PROMPT_SHA=d1bd81eefc355d91cbb1ca8292b3b76f36060d859cb67787dfe80f11a7622b06
SCHEMA_SHA=7c329bf55ff6e26c50cfa3346cf43d7e80f2237fec9423051b276e03718345a8
IDX=$((SLURM_ARRAY_TASK_ID + 1))
TAG=$(printf '%02d' "${IDX}")
TASK_DIR=${RUN_ROOT}/tasks/record_${TAG}
mkdir -p "${TASK_DIR}"
stage=initializing
process_exit=null
token_cap_reached=null
generated_tokens=null
success=0
started=$(date +%s)
write_receipt() {
  local shell_exit=$1
  TASK_DIR_VALUE=${TASK_DIR} STAGE_VALUE=${stage} PROCESS_EXIT_VALUE=${process_exit} TOKEN_CAP_VALUE=${token_cap_reached} GENERATED_VALUE=${generated_tokens} SHELL_EXIT_VALUE=${shell_exit} STARTED_VALUE=${started} SUCCESS_VALUE=${success} python3 - <<'PY'
import hashlib,json,os,pathlib,time
d=pathlib.Path(os.environ["TASK_DIR_VALUE"])
def meta(name):
 p=d/name
 if not p.is_file(): return None
 b=p.read_bytes(); return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
v=os.environ["PROCESS_EXIT_VALUE"]; t=os.environ["TOKEN_CAP_VALUE"]; g=os.environ["GENERATED_VALUE"]
payload={"schema_version":"linkup-cpu-fixed32-task-v1","status":"complete" if os.environ["SUCCESS_VALUE"]=="1" else "failed","stage":os.environ["STAGE_VALUE"],"job_id":os.environ.get("SLURM_ARRAY_JOB_ID"),"array_task_id":int(os.environ["SLURM_ARRAY_TASK_ID"]),"node":os.uname().nodename,"shell_exit":int(os.environ["SHELL_EXIT_VALUE"]),"process_exit":None if v=="null" else int(v),"generated_tokens":None if g=="null" else int(g),"token_cap_reached":None if t=="null" else bool(int(t)),"stop_reason":"token_budget_exhausted" if t=="1" else ("completed_below_cap_or_eos" if t=="0" else None),"started_at_epoch":int(os.environ["STARTED_VALUE"]),"ended_at_epoch":int(time.time()),"raw_stdout":meta("raw.stdout"),"inference_stderr":meta("inference.stderr"),"tokens":meta("tokens.txt"),"resources":{"cpus":8,"memory":"16G","accelerator":None,"wall_limit":"00:20:00"}}
(d/"TASK_RECEIPT.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY
}
on_exit(){ code=$?; write_receipt "${code}"; }
trap on_exit EXIT

stage=verify_artifacts
test -x "${RUNTIME}/llama-completion"
test -x "${RUNTIME}/llama-tokenize"
test -f "${MODEL}" && test "$(stat -c %s "${MODEL}")" = 5027783488
test -f "${RUN_ROOT}/PREPARE_RECEIPT_PRIVATE.json"

python - "${SOURCE_JSONL}" "${IDX}" "${PROMPT}" "${TASK_DIR}/prompt.txt" <<'PY'
import json, pathlib, sys
source, index, prompt, output = pathlib.Path(sys.argv[1]), int(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
lines = source.read_text(encoding="utf-8").splitlines()
if len(lines) != 32 or any(not line for line in lines):
    raise SystemExit(f"fixed32 source must contain exactly 32 nonblank rows; found {len(lines)}")
row = json.loads(lines[index - 1])
if set(row) != {"record_id", "original_text"} or not isinstance(row["original_text"], str):
    raise SystemExit(f"source row {index} is not the frozen record_id/original_text shape")
text = prompt.read_text(encoding="utf-8") + "\n\n<ORIGINAL_ADVERTISEMENT>\n" + row["original_text"] + "\n</ORIGINAL_ADVERTISEMENT>\n"
output.write_text(text, encoding="utf-8")
PY

"${RUNTIME}/llama-tokenize" -m "${MODEL}" -f "${TASK_DIR}/prompt.txt" --ids --show-count --offline \
  > "${TASK_DIR}/tokens.txt" 2> "${TASK_DIR}/tokenize.log"
TOKENS=$(python - "${TASK_DIR}/tokens.txt" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text(errors="replace")
m=re.search(r"(?:total number of tokens|token count)\D+(\d+)",s,re.I)
if not m: raise SystemExit("token count absent")
print(m.group(1))
PY
)
test "${TOKENS}" -le 12000 || { echo "input token cap exceeded: ${TOKENS}" >&2; exit 65; }

stage=inference
set +e
/usr/bin/time -v "${RUNTIME}/llama-completion" \
  -m "${MODEL}" -f "${TASK_DIR}/prompt.txt" -jf "${SCHEMA}" \
  -cnv -st --jinja --reasoning off --reasoning-budget 0 \
  --temp 0 --seed 424242 -n 2048 -c 16384 -t 8 -tb 8 \
  -ngl 0 --device none --no-context-shift --no-display-prompt --simple-io \
  --no-warmup --offline --perf \
  > "${TASK_DIR}/raw.stdout" 2> "${TASK_DIR}/inference.stderr"
process_exit=$?
set -e
test "${process_exit}" -eq 0
generated=$(python3 - "${TASK_DIR}/inference.stderr" <<'PY'
import pathlib,re,sys
s=pathlib.Path(sys.argv[1]).read_text(errors="replace")
m=re.search(r"(?<!prompt )eval time\s*=\s*[0-9.]+ ms\s*/\s*(\d+) runs",s)
print(m.group(1) if m else -1)
PY
)
generated_tokens=${generated}
if [ "${generated}" -lt 0 ]; then generated_tokens=null; token_cap_reached=null; exit 67
elif [ "${generated}" -ge 2048 ]; then token_cap_reached=1; exit 66
else token_cap_reached=0; fi
stage=complete
success=1
write_receipt 0
trap - EXIT
