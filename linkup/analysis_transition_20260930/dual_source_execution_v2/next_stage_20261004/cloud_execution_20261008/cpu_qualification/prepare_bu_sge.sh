#!/bin/bash -l
#$ -N linkup_q32_prep
#$ -cwd
#$ -j y
set -euo pipefail
: "${BU_ROOT:?}"; B=${BU_ROOT}/bundle; I=${BU_ROOT}/imported; R=${BU_ROOT}/run
umask 077; mkdir -p "${BU_ROOT}/model" "${R}" "${R}/merged/tasks" "${R}/python_vendor"
module load gcc/11.2.0 python3/3.8.10
export LD_LIBRARY_PATH="${B}/runtime/bin${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
export PYTHONPATH="${R}/python_vendor${PYTHONPATH:+:${PYTHONPATH}}"
status=failed; stage=initializing; started=$(date +%s)
receipt(){ code=$?; STATUS=$status STAGE=$stage CODE=$code STARTED=$started python3 - <<'PY'
import json,os,pathlib,time
p=pathlib.Path(os.environ["BU_ROOT"])/"BU_PREP_RECEIPT.json"
p.write_text(json.dumps({"schema_version":"linkup-bu-cpu-prep-v1","status":os.environ["STATUS"],"stage":os.environ["STAGE"],"exit_code":int(os.environ["CODE"]),"job_id":os.environ.get("JOB_ID"),"node":os.uname().nodename,"started_at_epoch":int(os.environ["STARTED"]),"ended_at_epoch":int(time.time()),"resources":{"slots":int(os.environ.get("NSLOTS","1")),"accelerator":None}},indent=2,sort_keys=True)+"\n")
PY
}; export BU_ROOT; trap receipt EXIT
stage=code_and_inputs
test -f "${BU_ROOT}/INPUT_TRANSPORT_COMPLETE"
cd "${B}"; sha256sum -c BU_TRANSPORT_SHA256.txt
test "$(sha256sum "${I}/prepared/SOURCE32_PRIVATE.jsonl"|awk '{print $1}')" = fc48f91cca944e54c0a319bed944e336521a414f746294fd0c3fd5db8b9e7d57
test "$(sha256sum "${I}/prepared/REFERENCE32_FINAL_CANDIDATES_PRIVATE.jsonl"|awk '{print $1}')" = dfb98eb1aae9f1ea2ffabc422544ec3a7515237522ba9bfb4b38c07e4a56120a
stage=python_vendor
tar -xf "${B}/python_vendor_v410.tar" -C "${R}/python_vendor" --strip-components=1
python3 -c 'from jsonschema import Draft202012Validator; assert Draft202012Validator'
stage=model_download
MODEL=${BU_ROOT}/model/Qwen3-8B-Q4_K_M.gguf
if [ ! -f "${MODEL}" ]; then
  TMP=${MODEL}.job-${JOB_ID}.partial
  timeout 1200 curl -fL --retry 2 --retry-delay 5 --connect-timeout 30 \
    'https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/7c41481f57cb95916b40956ab2f0b139b296d974/Qwen3-8B-Q4_K_M.gguf?download=true' -o "${TMP}"
  test "$(stat -c %s "${TMP}")" = 5027783488
  test "$(sha256sum "${TMP}"|awk '{print $1}')" = d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785
  chmod 400 "${TMP}"; mv "${TMP}" "${MODEL}"
fi
test "$(stat -c %s "${MODEL}")" = 5027783488
test "$(sha256sum "${MODEL}"|awk '{print $1}')" = d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785
stage=runtime
"${B}/runtime/bin/llama-completion" --version > "${R}/runtime-version.txt" 2>&1
"${B}/runtime/bin/llama-tokenize" --help > "${R}/tokenizer-help.txt" 2>&1
ldd "${B}/runtime/bin/llama-completion" > "${R}/runtime-ldd.txt"; ! grep -q 'not found' "${R}/runtime-ldd.txt"
stage=import_audit
python3 - "${I}" "${R}" <<'PY'
import hashlib,json,os,pathlib,sys
i,r=map(pathlib.Path,sys.argv[1:]); valid=[]; details=[]
for n in range(1,33):
 tag=f"record_{n:02d}"; d=i/"tasks"/tag; rp=d/"TASK_RECEIPT.json"; raw=d/"raw.stdout"; ok=False; reason="missing"
 if rp.is_file() and raw.is_file():
  try:
   x=json.loads(rp.read_text()); b=raw.read_bytes(); m=x.get("raw_stdout") or {}
   ok=x.get("status")=="complete" and x.get("process_exit")==0 and x.get("token_cap_reached") is False and m.get("bytes")==len(b) and m.get("sha256")==hashlib.sha256(b).hexdigest()
   reason="complete_hash_bound" if ok else "receipt_or_hash_incomplete"
  except Exception: reason="invalid_receipt"
 if ok: valid.append(n)
 target=d if ok else r/"bu_tasks"/tag
 link=r/"merged/tasks"/tag
 if os.path.lexists(str(link)): raise SystemExit(f"refusing existing merged link {link}")
 link.symlink_to(target)
 details.append({"index":n,"kunshan_reusable":ok,"reason":reason})
(r/"IMPORT_STATUS_PRIVATE.json").write_text(json.dumps({"valid_indices_1based":valid,"records":details},indent=2)+"\n")
PY
stage=complete; status=complete; trap - EXIT; receipt
