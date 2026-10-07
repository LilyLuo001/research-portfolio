#!/bin/bash
#SBATCH --job-name=linkup-qwen-route
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/local-inference-qwen-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/local-inference-qwen-%j.err
set -euo pipefail

LLAMA_COMMIT=42b021b4dc42be573f1e1463528532fc8294c650
MODEL_REPO=Qwen/Qwen3-8B-GGUF
MODEL_FILE=Qwen3-8B-Q4_K_M.gguf
MAX_DOWNLOAD_BYTES=8000000000
BASE=/public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/local_inference_20261007
INPUTS=/public/home/lilysharp/linkup_analysis_execution_oct02/code/next_stage_20261004/local_inference_20261007
RUN=${BASE}/run-${SLURM_JOB_ID}
PUBLIC=/public/home/lilysharp/linkup_analysis_execution_oct02/results/next_stage_20261004/local_inference_20261007/run-${SLURM_JOB_ID}
RUNTIME=${BASE}/runtime
MODEL_DIR=${BASE}/models/${MODEL_REPO//\//--}
PROMPT=${INPUTS}/extraction_v1_1.md
SCHEMA=${INPUTS}/extraction_v1_1.schema.json
SOURCE=${INPUTS}/synthetic_source.txt
stage=initializing
success=0
started_epoch=$(date +%s)

umask 077
mkdir -p "${RUN}" "${RUNTIME}" "${MODEL_DIR}"
mkdir -p "${PUBLIC}"

write_receipt() {
  receipt_status=$1
  exit_code=$2
  RECEIPT_STATUS=${receipt_status} RECEIPT_EXIT=${exit_code} RECEIPT_STAGE=${stage} \
  RECEIPT_START=${started_epoch} RECEIPT_END=$(date +%s) \
  RECEIPT_RUN=${RUN} RECEIPT_PUBLIC=${PUBLIC} RECEIPT_LLAMA_COMMIT=${LLAMA_COMMIT} \
  RECEIPT_MODEL_REPO=${MODEL_REPO} RECEIPT_MODEL_FILE=${MODEL_FILE} \
  python3 - <<'PY'
import hashlib, json, os, pathlib, time

def digest(path):
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return {"bytes": p.stat().st_size, "sha256": h.hexdigest()}

run = pathlib.Path(os.environ["RECEIPT_RUN"])
public = pathlib.Path(os.environ["RECEIPT_PUBLIC"])
model_revision_path = run / "model_revision.txt"
model_revision = model_revision_path.read_text().strip() if model_revision_path.is_file() else None
payload = {
    "schema_version": "linkup-local-inference-route-receipt-v1",
    "status": os.environ["RECEIPT_STATUS"],
    "failure_stage_or_final_stage": os.environ["RECEIPT_STAGE"],
    "exit_code": int(os.environ["RECEIPT_EXIT"]),
    "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "host": os.uname().nodename,
    "resources": {"cpus": int(os.environ.get("SLURM_CPUS_PER_TASK", "0")), "memory_request": "32G", "walltime_limit": "01:00:00"},
    "elapsed_seconds": int(os.environ["RECEIPT_END"]) - int(os.environ["RECEIPT_START"]),
    "runtime": {
        "repository": "https://github.com/ggml-org/llama.cpp",
        "commit": os.environ["RECEIPT_LLAMA_COMMIT"],
        "source_archive": digest(run / "llama.cpp.tar.gz"),
        "binary": digest(run / "llama-cli"),
        "version_text": (run / "llama_version.txt").read_text(errors="replace")[:2000] if (run / "llama_version.txt").is_file() else None,
    },
    "model": {
        "repository": os.environ["RECEIPT_MODEL_REPO"],
        "revision": model_revision,
        "filename": os.environ["RECEIPT_MODEL_FILE"],
        "artifact": digest(run / "model.gguf"),
        "license": "Apache-2.0 (per official model card; LICENSE snapshot separately hashed)",
        "license_snapshot": digest(run / "MODEL_LICENSE"),
    },
    "measurement_contract": {
        "prompt": digest(run / "prompt.md"),
        "schema": digest(run / "schema.json"),
        "source_text": digest(run / "source.txt"),
        "record_id": "route-synthetic-001",
        "documents_processed": 1,
        "purpose": "routeability and throughput only; no quality certification",
    },
    "inference": {
        "started_epoch": int((run / "inference_started_epoch.txt").read_text()) if (run / "inference_started_epoch.txt").is_file() else None,
        "ended_epoch": int((run / "inference_ended_epoch.txt").read_text()) if (run / "inference_ended_epoch.txt").is_file() else None,
        "response": digest(run / "response.json"),
        "stderr": digest(run / "inference.stderr"),
    },
    "limits": {"download_bytes_max": 8000000000, "documents_max": 4, "bulk_run_started": False},
    "notes": ["CPU-only route; no claim that Hygon DCU is AMD-compatible.", "Successful execution, if any, does not validate semantic accuracy."],
}
rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
(run / "run_receipt.json").write_text(rendered)
(public / "run_receipt.json").write_text(rendered)
PY
}

on_exit() {
  code=$?
  if [ "${success}" -ne 1 ]; then
    write_receipt FAILED "${code}"
  fi
}
trap on_exit EXIT

stage=verify_inputs
test "$(sha256sum "${PROMPT}" | awk '{print $1}')" = 51ff8202bb519b4d4f2fc455dbc18de3f6deccc3a32abba4ca63792dfadcefb7
test "$(sha256sum "${SCHEMA}" | awk '{print $1}')" = fd3a0add7e02ad2d37303cc1ce2e3241e5ec916723847a47581b45283917ee8c
cp "${PROMPT}" "${RUN}/prompt.md"
cp "${SCHEMA}" "${RUN}/schema.json"
cp "${SOURCE}" "${RUN}/source.txt"

stage=enable_compute_network
source "${HOME}/proxy.sh"

stage=install_pinned_cmake
CMAKE_VERSION=3.31.6
CMAKE_ARCHIVE=cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz
CMAKE_URL=https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/${CMAKE_ARCHIVE}
CMAKE_HASH_URL=https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-SHA-256.txt
if [ ! -x "${RUNTIME}/cmake-${CMAKE_VERSION}-linux-x86_64/bin/cmake" ]; then
  curl -fL --connect-timeout 30 --max-time 600 "${CMAKE_HASH_URL}" -o "${RUN}/cmake-sha256.txt"
  curl -fL --connect-timeout 30 --max-time 600 "${CMAKE_URL}" -o "${RUN}/${CMAKE_ARCHIVE}"
  expected=$(awk -v name="${CMAKE_ARCHIVE}" '$2==name {print $1}' "${RUN}/cmake-sha256.txt")
  test -n "${expected}"
  test "$(sha256sum "${RUN}/${CMAKE_ARCHIVE}" | awk '{print $1}')" = "${expected}"
  tar -xzf "${RUN}/${CMAKE_ARCHIVE}" -C "${RUNTIME}"
fi
CMAKE=${RUNTIME}/cmake-${CMAKE_VERSION}-linux-x86_64/bin/cmake
"${CMAKE}" --version

stage=download_pinned_llama_source
LLAMA_ARCHIVE_URL=https://github.com/ggml-org/llama.cpp/archive/${LLAMA_COMMIT}.tar.gz
curl -fL --connect-timeout 30 --max-time 600 "${LLAMA_ARCHIVE_URL}" -o "${RUN}/llama.cpp.tar.gz"
mkdir -p "${RUN}/src"
tar -xzf "${RUN}/llama.cpp.tar.gz" --strip-components=1 -C "${RUN}/src"

stage=build_cpu_runtime
"${CMAKE}" -S "${RUN}/src" -B "${RUN}/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_BLAS=OFF \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON \
  -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=ON
"${CMAKE}" --build "${RUN}/build" --config Release -j 16 --target llama-cli
cp "${RUN}/build/bin/llama-cli" "${RUN}/llama-cli"
"${RUN}/llama-cli" --version > "${RUN}/llama_version.txt" 2>&1

stage=resolve_pinned_model_revision
curl -fL --connect-timeout 30 --max-time 120 \
  "https://huggingface.co/api/models/${MODEL_REPO}/revision/main" -o "${RUN}/model_api.json"
python3 - "${RUN}/model_api.json" "${RUN}/model_revision.txt" <<'PY'
import json, pathlib, re, sys
revision = json.loads(pathlib.Path(sys.argv[1]).read_text())["sha"]
if not re.fullmatch(r"[0-9a-f]{40}", revision):
    raise SystemExit("model API returned a non-commit revision")
pathlib.Path(sys.argv[2]).write_text(revision + "\n")
PY
MODEL_REVISION=$(cat "${RUN}/model_revision.txt")

stage=download_pinned_model
MODEL_PATH=${MODEL_DIR}/${MODEL_REVISION}-${MODEL_FILE}
if [ ! -f "${MODEL_PATH}" ]; then
  curl -fL --connect-timeout 30 --max-time 2400 \
    "https://huggingface.co/${MODEL_REPO}/resolve/${MODEL_REVISION}/${MODEL_FILE}?download=true" \
    -o "${MODEL_PATH}.partial"
  model_bytes=$(stat -c %s "${MODEL_PATH}.partial")
  test "${model_bytes}" -lt "${MAX_DOWNLOAD_BYTES}"
  mv "${MODEL_PATH}.partial" "${MODEL_PATH}"
fi
ln "${MODEL_PATH}" "${RUN}/model.gguf"
curl -fL --connect-timeout 30 --max-time 120 \
  "https://huggingface.co/${MODEL_REPO}/resolve/${MODEL_REVISION}/LICENSE" -o "${RUN}/MODEL_LICENSE"
total_downloaded=$(du -cb "${RUN}/llama.cpp.tar.gz" "${RUN}/${CMAKE_ARCHIVE}" "${RUN}/model.gguf" "${RUN}/MODEL_LICENSE" 2>/dev/null | tail -1 | awk '{print $1}')
test "${total_downloaded}" -lt "${MAX_DOWNLOAD_BYTES}"

stage=compose_unchanged_prompt_with_synthetic_record
SOURCE_SHA=$(sha256sum "${RUN}/source.txt" | awk '{print $1}')
cp "${RUN}/prompt.md" "${RUN}/request.txt"
printf '\n\nCaller-supplied record_id: route-synthetic-001\nCaller-supplied source_text_sha256: %s\nADVERTISEMENT_TEXT_BEGIN\n' "${SOURCE_SHA}" >> "${RUN}/request.txt"
cat "${RUN}/source.txt" >> "${RUN}/request.txt"
printf 'ADVERTISEMENT_TEXT_END\n/no_think\n' >> "${RUN}/request.txt"

stage=run_one_document_inference
date +%s > "${RUN}/inference_started_epoch.txt"
timeout 900 "${RUN}/llama-cli" \
  -m "${RUN}/model.gguf" -f "${RUN}/request.txt" \
  -t 16 -c 4096 -n 1024 --no-display-prompt --no-conversation --jinja \
  --temp 0.7 --top-k 20 --top-p 0.8 --min-p 0 --presence-penalty 1.5 \
  --json-schema "$(cat "${RUN}/schema.json")" \
  > "${RUN}/response.json" 2> "${RUN}/inference.stderr"
date +%s > "${RUN}/inference_ended_epoch.txt"

stage=validate_json_route
python3 - "${RUN}/response.json" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
if data.get("record_id") != "route-synthetic-001":
    raise SystemExit("response record_id mismatch")
if not isinstance(data.get("experience_findings"), list):
    raise SystemExit("response lacks experience_findings array")
PY
cp "${RUN}/response.json" "${PUBLIC}/synthetic_response.json"
cp "${RUN}/inference.stderr" "${PUBLIC}/inference.stderr"

stage=complete
success=1
write_receipt PASS 0
trap - EXIT
