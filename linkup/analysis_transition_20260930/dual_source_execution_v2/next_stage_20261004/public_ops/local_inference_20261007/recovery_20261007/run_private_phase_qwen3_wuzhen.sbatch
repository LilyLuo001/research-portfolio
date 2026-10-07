#!/bin/bash
#SBATCH --job-name=linkup-qwen3-route
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:2
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/inference-%j.out
#SBATCH --error=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/inference-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u

: "${PHASE:?submit with PHASE=synthetic or pilot4}"
: "${EXPECTED_RECORDS:?submit with EXPECTED_RECORDS}"
case "${PHASE}" in synthetic|pilot4) ;; *) echo "invalid PHASE" >&2; exit 64;; esac

BASE=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery
RUNTIME=${BASE}/build-run-46032322/build/bin
MODEL=${BASE}/staged_artifacts/Qwen3-8B-Q4_K_M.gguf
PRIVATE_BASE=${BASE}/private_eval
PROMPTS=${PRIVATE_BASE}/${PHASE}/prompts
SCHEMA=${PRIVATE_BASE}/contract/extraction_v1_1.schema.json
RUN=${PRIVATE_BASE}/${PHASE}/run-${SLURM_JOB_ID}
MODEL_SHA=d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785
CTX=16384
OUTPUT_BUDGET=4096
MAX_INPUT_TOKENS=12000
started=$(date +%s)
stage=initializing
success=0
umask 077
mkdir -p "${RUN}"

write_receipt() {
  local status=$1
  local code=$2
  STATUS=${status} EXIT_CODE=${code} STAGE=${stage} STARTED=${started} ENDED=$(date +%s) \
  RUN_DIR=${RUN} PHASE_VALUE=${PHASE} EXPECTED=${EXPECTED_RECORDS} MODEL_PATH=${MODEL} \
  CTX_VALUE=${CTX} OUTPUT_VALUE=${OUTPUT_BUDGET} python - <<'PY'
import hashlib, json, os, pathlib, re

run = pathlib.Path(os.environ["RUN_DIR"])
def digest(path):
    path = pathlib.Path(path)
    if not path.is_file(): return None
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""): h.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": h.hexdigest()}

records = []
for path in sorted(run.glob("record_*.tokens.txt")):
    match = re.search(r"(?:total number of tokens|token count)\D+(\d+)", path.read_text(errors="replace"), re.I)
    index = path.name.split(".")[0]
    raw = run / f"{index}.raw.json"
    log = run / f"{index}.inference.log"
    log_text = log.read_text(errors="replace") if log.is_file() else ""
    prompt_perf = re.search(r"prompt eval time\s*=\s*([0-9.]+) ms\s*/\s*(\d+) tokens.*?([0-9.]+) tokens per second", log_text)
    eval_perf = re.search(r"(?<!prompt )eval time\s*=\s*([0-9.]+) ms\s*/\s*(\d+) runs.*?([0-9.]+) tokens per second", log_text)
    records.append({"index": index, "input_tokens": int(match.group(1)) if match else None,
                    "prompt_eval_seconds": float(prompt_perf.group(1)) / 1000 if prompt_perf else None,
                    "prompt_eval_tokens": int(prompt_perf.group(2)) if prompt_perf else None,
                    "prompt_tokens_per_second": float(prompt_perf.group(3)) if prompt_perf else None,
                    "generation_seconds": float(eval_perf.group(1)) / 1000 if eval_perf else None,
                    "generation_tokens": int(eval_perf.group(2)) if eval_perf else None,
                    "generation_tokens_per_second": float(eval_perf.group(3)) if eval_perf else None,
                    "raw_output": digest(raw), "log": digest(log)})
elapsed = int(os.environ["ENDED"]) - int(os.environ["STARTED"])
payload = {
    "schema_version": "linkup-local-qwen3-route-v1",
    "status": os.environ["STATUS"], "exit_code": int(os.environ["EXIT_CODE"]),
    "stage": os.environ["STAGE"], "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "phase": os.environ["PHASE_VALUE"], "host": os.uname().nodename,
    "elapsed_seconds": elapsed,
    "resources": {"cpus": 16, "requested_dcus": 2, "allocated_dcu_card_hours": 2 * elapsed / 3600,
                  "memory": "32G", "walltime_limit": "01:00:00"},
    "context": {"ctx_size": int(os.environ["CTX_VALUE"]), "output_budget": int(os.environ["OUTPUT_VALUE"]),
                "context_shift": False},
    "expected_records": int(os.environ["EXPECTED"]), "records": records,
    "model": {"repository": "Qwen/Qwen3-8B-GGUF", "revision": "7c41481f57cb95916b40956ab2f0b139b296d974",
              "file": "Qwen3-8B-Q4_K_M.gguf", "artifact": digest(os.environ["MODEL_PATH"])},
    "runtime": {"commit": "42b021b4dc42be573f1e1463528532fc8294c650", "executable": "llama-completion"},
    "device_inventory": digest(run / "device_inventory.txt"),
    "sampling": {"temperature": 0, "seed": 424242, "reasoning": "off", "json_schema_constrained": True},
}
(run / "ROUTE_RECEIPT.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}
on_exit() {
  code=$?
  if [ "${success}" -ne 1 ]; then write_receipt FAILED "${code}"; fi
}
trap on_exit EXIT

stage=verify_artifacts
test "$(stat -c %s "${MODEL}")" = 5027783488
test "$(sha256sum "${MODEL}" | awk '{print $1}')" = "${MODEL_SHA}"
test -x "${RUNTIME}/llama-completion"
test -x "${RUNTIME}/llama-tokenize"
test -f "${SCHEMA}"
mapfile -t prompt_files < <(find "${PROMPTS}" -maxdepth 1 -type f -name 'record_*.prompt.txt' | sort)
test "${#prompt_files[@]}" -eq "${EXPECTED_RECORDS}"

stage=read_only_device_inventory
{
  echo "GPU or DCU allocation is scheduler-required; this runtime is CPU-only."
  command -v hy-smi || true
  command -v rocm-smi || true
  command -v hipcc || true
  command -v dtk-smi || true
  module list 2>&1 || true
} > "${RUN}/device_inventory.txt"

stage=tokenize_and_infer
for prompt in "${prompt_files[@]}"; do
  index=$(basename "${prompt}" .prompt.txt)
  "${RUNTIME}/llama-tokenize" -m "${MODEL}" -f "${prompt}" --ids --show-count --offline \
    > "${RUN}/${index}.tokens.txt" 2> "${RUN}/${index}.tokenize.log"
  tokens=$(python - "${RUN}/${index}.tokens.txt" <<'PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text(errors="replace")
match = re.search(r"(?:total number of tokens|token count)\D+(\d+)", text, re.I)
if not match: raise SystemExit("token count absent")
print(match.group(1))
PY
)
  if [ "${tokens}" -gt "${MAX_INPUT_TOKENS}" ]; then
    echo "${index}: ${tokens} input tokens exceeds ${MAX_INPUT_TOKENS}; refusing truncation" >&2
    exit 65
  fi
  prompt_value=$(cat "${prompt}")
  /usr/bin/time -v "${RUNTIME}/llama-completion" \
    -m "${MODEL}" -p "${prompt_value}" -jf "${SCHEMA}" \
    -cnv -st --jinja --reasoning off --reasoning-budget 0 \
    --temp 0 --seed 424242 -n "${OUTPUT_BUDGET}" -c "${CTX}" \
    -t 16 -tb 16 -ngl 0 --device none --no-context-shift \
    --no-display-prompt --simple-io --no-warmup --offline --perf \
    > "${RUN}/${index}.raw.json" 2> "${RUN}/${index}.inference.log"
done

stage=complete
success=1
write_receipt PASS_PENDING_EXACT_VALIDATION 0
trap - EXIT
