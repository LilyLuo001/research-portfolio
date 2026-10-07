#!/bin/bash
#SBATCH --job-name=linkup-llama-build
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:2
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/build-%j.out
#SBATCH --error=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery/logs/build-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u

LLAMA_COMMIT=42b021b4dc42be573f1e1463528532fc8294c650
BASE=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery
STAGED=${BASE}/staged_artifacts
RUN=${BASE}/build-run-${SLURM_JOB_ID}
TOOLROOT=${BASE}/toolchain_gcc11_payload_v2/opt/rh/devtoolset-11/root/usr
CMAKE_ARCHIVE=${STAGED}/cmake-3.31.6-linux-x86_64.tar.gz
SOURCE_ARCHIVE=${STAGED}/llama-${LLAMA_COMMIT}.tar.gz
stage=initializing
started=$(date +%s)
success=0
umask 077
mkdir -p "${RUN}"

write_receipt() {
  receipt_status=$1
  exit_code=$2
  STATUS=${receipt_status} EXIT_CODE=${exit_code} STAGE=${stage} STARTED=${started} ENDED=$(date +%s) \
  RUN_DIR=${RUN} LLAMA_COMMIT_VALUE=${LLAMA_COMMIT} python - <<'PY'
import hashlib, json, os, pathlib

run = pathlib.Path(os.environ["RUN_DIR"])
def digest(path):
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return {"bytes": p.stat().st_size, "sha256": h.hexdigest()}

payload = {
    "schema_version": "linkup-pinned-llama-build-receipt-v1",
    "status": os.environ["STATUS"],
    "stage": os.environ["STAGE"],
    "exit_code": int(os.environ["EXIT_CODE"]),
    "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "host": os.uname().nodename,
    "resources": {"cpus": 16, "requested_dcus": 2, "memory": "32G", "walltime_limit": "01:00:00"},
    "elapsed_seconds": int(os.environ["ENDED"]) - int(os.environ["STARTED"]),
    "runtime": {
        "repository": "https://github.com/ggml-org/llama.cpp",
        "commit": os.environ["LLAMA_COMMIT_VALUE"],
        "source_archive": digest(run / "llama-source.tar.gz"),
        "intended_executable": "llama-completion",
        "binary": digest(run / "llama-completion"),
        "tokenizer_binary": digest(run / "llama-tokenize"),
        "version": (run / "llama-version.txt").read_text(errors="replace")[:2000] if (run / "llama-version.txt").is_file() else None,
        "help": (run / "llama-help.txt").read_text(errors="replace")[:12000] if (run / "llama-help.txt").is_file() else None,
    },
    "toolchain": {
        "gcc_version": (run / "gcc-version.txt").read_text(errors="replace").strip() if (run / "gcc-version.txt").is_file() else None,
        "cmake_archive": digest(run / "cmake.tar.gz"),
        "cmake_version": "3.31.6"
    },
    "inference": {"documents_attempted": 0, "documents_completed": 0, "model_downloaded": False},
    "purpose": "Pinned CPU runtime build gate before any multi-gigabyte model transfer; no semantic result."
}
(run / "BUILD_RECEIPT.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

on_exit() {
  code=$?
  if [ "${success}" -ne 1 ]; then
    write_receipt FAILED "${code}"
  fi
}
trap on_exit EXIT

stage=verify_staged_artifacts
test "$(sha256sum "${CMAKE_ARCHIVE}" | awk '{print $1}')" = 5a1133ff103c71eb5120e2cc3de922733e7d8a26a98ae716397e8676adb367bf
test "$(sha256sum "${SOURCE_ARCHIVE}" | awk '{print $1}')" = 0ebbca14b5d5db9d236ed72e15fe6be9f97755136126d04196bfbc5130e77c6e
ln "${CMAKE_ARCHIVE}" "${RUN}/cmake.tar.gz"
ln "${SOURCE_ARCHIVE}" "${RUN}/llama-source.tar.gz"

stage=prepare_toolchain
export PATH=${TOOLROOT}/bin:${PATH}
export LD_LIBRARY_PATH=${TOOLROOT}/lib64:${TOOLROOT}/lib:${LD_LIBRARY_PATH:-}
unset CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH INCLUDE LIBRARY_PATH
g++ --version | sed -n '1p' > "${RUN}/gcc-version.txt"
tar -xzf "${RUN}/cmake.tar.gz" -C "${RUN}"
tar -xzf "${RUN}/llama-source.tar.gz" --strip-components=1 -C "${RUN}/src" 2>/dev/null || {
  mkdir -p "${RUN}/src"
  tar -xzf "${RUN}/llama-source.tar.gz" --strip-components=1 -C "${RUN}/src"
}
CMAKE=${RUN}/cmake-3.31.6-linux-x86_64/bin/cmake

stage=configure_cpu_runtime
"${CMAKE}" -S "${RUN}/src" -B "${RUN}/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_BLAS=OFF \
  -DCMAKE_C_COMPILER="${TOOLROOT}/bin/gcc" \
  -DCMAKE_CXX_COMPILER="${TOOLROOT}/bin/g++" \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF \
  -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_TOOLS=ON

stage=build_cpu_runtime
"${CMAKE}" --build "${RUN}/build" --config Release -j 16 --target llama-completion llama-tokenize
cp "${RUN}/build/bin/llama-completion" "${RUN}/llama-completion"
cp "${RUN}/build/bin/llama-tokenize" "${RUN}/llama-tokenize"
"${RUN}/llama-completion" --version > "${RUN}/llama-version.txt" 2>&1
"${RUN}/llama-completion" --help > "${RUN}/llama-help.txt" 2>&1

stage=complete
success=1
write_receipt BUILD_PASS_AWAITING_PINNED_MODEL 0
trap - EXIT
