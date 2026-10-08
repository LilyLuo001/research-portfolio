#!/bin/bash
#SBATCH --job-name=linkup-q32-prep
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
set -euo pipefail
set +u; source /etc/profile >/dev/null 2>&1 || true; module load python/3.8.10 >/dev/null 2>&1 || true; set -u
: "${BUNDLE:?}"; : "${RUN_ROOT:?}"
export RUN_ROOT
umask 077; mkdir -p "${RUN_ROOT}"
status=failed; stage=initializing; started=$(date +%s)
receipt(){ code=$?; STATUS=$status STAGE=$stage CODE=$code STARTED=$started python3 - <<'PY'
import json,os,pathlib,time
p=pathlib.Path(os.environ["RUN_ROOT"])/"PREP_JOB_RECEIPT.json"
p.write_text(json.dumps({"status":os.environ["STATUS"],"stage":os.environ["STAGE"],"exit_code":int(os.environ["CODE"]),"job_id":os.environ.get("SLURM_JOB_ID"),"node":os.uname().nodename,"started_at_epoch":int(os.environ["STARTED"]),"ended_at_epoch":int(time.time()),"resources":{"cpus":2,"memory":"4G","accelerator":None}},indent=2)+"\n")
PY
}; trap receipt EXIT
stage=assemble_model
cd "${BUNDLE}"
if [ ! -f model/Qwen3-8B-Q4_K_M.gguf ]; then
  for i in 0 1 2 3; do test "$(stat -c %s model/part.${i})" = 1256945872; done
  cat model/part.0 model/part.1 model/part.2 model/part.3 > model/Qwen3-8B-Q4_K_M.gguf
  chmod 400 model/Qwen3-8B-Q4_K_M.gguf
fi
stage=checksums
sha256sum -c TRANSPORT_SHA256.txt
stage=runtime_compatibility
export LD_LIBRARY_PATH="${BUNDLE}/runtime/bin:${BUNDLE}/runtime/gcc11-lib64:${BUNDLE}/runtime/gcc11-lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
"${BUNDLE}/runtime/bin/llama-completion" --version > "${RUN_ROOT}/runtime-version.txt" 2>&1
"${BUNDLE}/runtime/bin/llama-tokenize" --help > "${RUN_ROOT}/tokenizer-help.txt" 2>&1
ldd "${BUNDLE}/runtime/bin/llama-completion" > "${RUN_ROOT}/runtime-ldd.txt"
! grep -q 'not found' "${RUN_ROOT}/runtime-ldd.txt"
stage=python_vendor
mkdir -p "${RUN_ROOT}/python_vendor"
tar -xf "${BUNDLE}/python_vendor_v410.tar" -C "${RUN_ROOT}/python_vendor" --strip-components=1
export PYTHONPATH="${RUN_ROOT}/python_vendor${PYTHONPATH:+:${PYTHONPATH}}"
python3 -c 'import jsonschema' > "${RUN_ROOT}/python-dependencies.txt" 2>&1
stage=materialize_fixed32
python3 "${BUNDLE}/code/prepare_fixed32_inputs.py" --source128 "${BUNDLE}/archive/COMBINED_SOURCE_PRIVATE.jsonl" --reference128 "${BUNDLE}/archive/FINAL_CANDIDATES_PRIVATE.jsonl" --output "${RUN_ROOT}/prepared"
cp "${RUN_ROOT}/prepared/PREPARE_RECEIPT_PRIVATE.json" "${RUN_ROOT}/PREPARE_RECEIPT_PRIVATE.json"
stage=complete; status=complete; trap - EXIT; receipt
