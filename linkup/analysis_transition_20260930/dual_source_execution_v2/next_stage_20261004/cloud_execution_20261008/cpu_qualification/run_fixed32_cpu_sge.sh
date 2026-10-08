#!/bin/bash -l
#$ -N linkup_q32_cpu
#$ -cwd
#$ -j y
set -euo pipefail
: "${BU_ROOT:?}"; : "${SGE_TASK_ID:?}"; test "${NSLOTS:-0}" = 8
B=${BU_ROOT}/bundle; I=${BU_ROOT}/imported; R=${BU_ROOT}/run; IDX=${SGE_TASK_ID}; TAG=$(printf '%02d' "${IDX}")
module load gcc/11.2.0 python3/3.8.10
export LD_LIBRARY_PATH="${B}/runtime/bin${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
SOURCE=${I}/prepared/SOURCE32_PRIVATE.jsonl; MODEL=${BU_ROOT}/model/Qwen3-8B-Q4_K_M.gguf
PROMPT=${B}/archive/production_standard_20261008/EXTRACTION_PROMPT.md; SCHEMA=${B}/archive/compact_measurement_20261007/schema/compact_model_output.schema.json
IMPORTED=${I}/tasks/record_${TAG}; TASK=${R}/bu_tasks/record_${TAG}; umask 077
if python3 - "${IMPORTED}" <<'PY'
import hashlib,json,pathlib,sys
d=pathlib.Path(sys.argv[1]); rp=d/"TASK_RECEIPT.json"; raw=d/"raw.stdout"
if not (rp.is_file() and raw.is_file()): raise SystemExit(1)
x=json.loads(rp.read_text()); b=raw.read_bytes(); m=x.get("raw_stdout") or {}
ok=x.get("status")=="complete" and x.get("process_exit")==0 and x.get("token_cap_reached") is False and m.get("bytes")==len(b) and m.get("sha256")==hashlib.sha256(b).hexdigest()
raise SystemExit(0 if ok else 1)
PY
then mkdir -p "${TASK}"; printf '{"status":"reused_verified_kunshan","record_index_1based":%s}\n' "${IDX}" > "${TASK}/BU_SKIP_RECEIPT.json"; exit 0; fi
mkdir -p "${TASK}"; stage=initializing; process_exit=null; token_cap_reached=null; generated_tokens=null; success=0; started=$(date +%s)
write_receipt(){ shell_exit=$1; TASK_DIR_VALUE=${TASK} STAGE_VALUE=${stage} PROCESS_EXIT_VALUE=${process_exit} TOKEN_CAP_VALUE=${token_cap_reached} GENERATED_VALUE=${generated_tokens} SHELL_EXIT_VALUE=${shell_exit} STARTED_VALUE=${started} SUCCESS_VALUE=${success} python3 - <<'PY'
import hashlib,json,os,pathlib,time
d=pathlib.Path(os.environ["TASK_DIR_VALUE"])
def meta(n):
 p=d/n
 if not p.is_file(): return None
 b=p.read_bytes(); return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
v,t,g=os.environ["PROCESS_EXIT_VALUE"],os.environ["TOKEN_CAP_VALUE"],os.environ["GENERATED_VALUE"]
x={"schema_version":"linkup-cpu-fixed32-task-v1","execution_location":"BU_SCC","status":"complete" if os.environ["SUCCESS_VALUE"]=="1" else "failed","stage":os.environ["STAGE_VALUE"],"job_id":os.environ.get("JOB_ID"),"array_task_id":int(os.environ["SGE_TASK_ID"])-1,"node":os.uname().nodename,"shell_exit":int(os.environ["SHELL_EXIT_VALUE"]),"process_exit":None if v=="null" else int(v),"generated_tokens":None if g=="null" else int(g),"token_cap_reached":None if t=="null" else bool(int(t)),"stop_reason":"token_budget_exhausted" if t=="1" else ("completed_below_cap_or_eos" if t=="0" else None),"started_at_epoch":int(os.environ["STARTED_VALUE"]),"ended_at_epoch":int(time.time()),"raw_stdout":meta("raw.stdout"),"inference_stderr":meta("inference.stderr"),"tokens":meta("tokens.txt"),"resources":{"cpus":8,"memory":"2G_per_core","accelerator":None,"wall_limit":"00:20:00"}}
(d/"TASK_RECEIPT.json").write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
PY
}; trap 'c=$?; write_receipt "$c"' EXIT
stage=prompt
python3 - "${SOURCE}" "${IDX}" "${PROMPT}" "${TASK}/prompt.txt" <<'PY'
import json,pathlib,sys
s,n,p,o=pathlib.Path(sys.argv[1]),int(sys.argv[2]),pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[4]); ls=s.read_text().splitlines()
if len(ls)!=32 or any(not x for x in ls): raise SystemExit("source count")
r=json.loads(ls[n-1]); o.write_text(p.read_text()+"\n\n<ORIGINAL_ADVERTISEMENT>\n"+r["original_text"]+"\n</ORIGINAL_ADVERTISEMENT>\n")
PY
"${B}/runtime/bin/llama-tokenize" -m "${MODEL}" -f "${TASK}/prompt.txt" --ids --show-count --offline > "${TASK}/tokens.txt" 2> "${TASK}/tokenize.log"
TOKENS=$(python3 - "${TASK}/tokens.txt" <<'PY'
import pathlib,re,sys
m=re.search(r"(?:total number of tokens|token count)\D+(\d+)",pathlib.Path(sys.argv[1]).read_text(errors="replace"),re.I)
if not m: raise SystemExit("token count absent")
print(m.group(1))
PY
); test "${TOKENS}" -le 12000
stage=inference; set +e
/usr/bin/time -v "${B}/runtime/bin/llama-completion" -m "${MODEL}" -f "${TASK}/prompt.txt" -jf "${SCHEMA}" -cnv -st --jinja --reasoning off --reasoning-budget 0 --temp 0 --seed 424242 -n 2048 -c 16384 -t 8 -tb 8 -ngl 0 --device none --no-context-shift --no-display-prompt --simple-io --no-warmup --offline --perf > "${TASK}/raw.stdout" 2> "${TASK}/inference.stderr"
process_exit=$?; set -e; test "${process_exit}" -eq 0
generated_tokens=$(python3 - "${TASK}/inference.stderr" <<'PY'
import pathlib,re,sys
m=re.search(r"(?<!prompt )eval time\s*=\s*[0-9.]+ ms\s*/\s*(\d+) runs",pathlib.Path(sys.argv[1]).read_text(errors="replace")); print(m.group(1) if m else -1)
PY
)
if [ "${generated_tokens}" -lt 0 ]; then generated_tokens=null; exit 67; elif [ "${generated_tokens}" -ge 2048 ]; then token_cap_reached=1; exit 66; else token_cap_reached=0; fi
stage=complete; success=1; write_receipt 0; trap - EXIT
