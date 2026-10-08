#!/bin/bash
#SBATCH --job-name=linkup-llama-hip-build
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=hip-build-%j.out
#SBATCH --error=hip-build-%j.err

set -euo pipefail
export LC_ALL=C
export PATH=/sbin:/usr/sbin:${PATH}
umask 077

LLAMA_COMMIT=42b021b4dc42be573f1e1463528532fc8294c650
RECOVERY=${HOME}/private/next_stage_20261004/local_inference_20261007/recovery
STAGED=${RECOVERY}/staged_artifacts
TOOLROOT=${RECOVERY}/toolchain_gcc11_payload_v2/opt/rh/devtoolset-11/root/usr
SOURCE_ARCHIVE=${STAGED}/llama-${LLAMA_COMMIT}.tar.gz
CMAKE_ARCHIVE=${STAGED}/cmake-3.31.6-linux-x86_64.tar.gz
BASE=${HOME}/private/next_stage_20261004/cloud_execution_20261008/runtime
RUN=${BASE}/hip-build-run-${SLURM_JOB_ID}
mkdir -p "${RUN}/src"
stage=initializing
started=$(date +%s)
success=0

write_receipt() {
  status=$1
  code=$2
  STATUS=${status} EXIT_CODE=${code} STAGE=${stage} STARTED=${started} ENDED=$(date +%s) \
    RUN_DIR=${RUN} LLAMA_COMMIT_VALUE=${LLAMA_COMMIT} python - <<'PY'
import hashlib, json, os, pathlib
run = pathlib.Path(os.environ["RUN_DIR"])
def digest(path):
    p = pathlib.Path(path)
    if not p.is_file(): return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""): h.update(chunk)
    return {"bytes": p.stat().st_size, "sha256": h.hexdigest()}
def text(name, limit=20000):
    p = run / name
    return p.read_text(errors="replace")[:limit] if p.is_file() else None
payload = {
  "schema_version": "linkup-wuzhen-llama-hip-build-v1",
  "status": os.environ["STATUS"], "stage": os.environ["STAGE"],
  "exit_code": int(os.environ["EXIT_CODE"]), "job_id": os.environ.get("SLURM_JOB_ID"),
  "node": os.uname().nodename,
  "resources": {"cpus": 8, "memory": "16G", "requested_dcus": 1, "time_limit": "00:30:00", "compile_parallelism": 8},
  "source": {"commit": os.environ["LLAMA_COMMIT_VALUE"], "archive": digest(run / "llama-source.tar.gz")},
  "toolchain": {"module": "compiler/dtk/26.04", "hip_version": text("hip-version.txt"), "gpu_target": text("gpu-target.txt"), "cmake_version": text("cmake-version.txt"), "gcc_version": text("gcc-version.txt")},
  "runtime": {"binary": digest(run / "llama-completion"), "hip_library": digest(run / "libggml-hip.so"), "linkage": text("runtime-ldd.txt"), "device_enumeration": text("device-enumeration.txt")},
  "logs": {"prerequisites": text("prerequisites.txt"), "configure_tail": text("configure-tail.txt"), "build_tail": text("build-tail.txt")},
  "inference": {"models_loaded": 0, "documents_attempted": 0, "documents_completed": 0}
}
(run / "HIP_BUILD_RECEIPT.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

on_exit() {
  code=$?
  if [ "${success}" -ne 1 ]; then write_receipt FAILED "${code}"; fi
}
trap on_exit EXIT

stage=load_toolchain
set +u
source /etc/profile >/dev/null 2>&1 || true
module purge >/dev/null 2>&1 || true
module load python/3.8.10 compiler/dtk/26.04
set -u
export PATH=/sbin:/usr/sbin:${TOOLROOT}/bin:${PATH}
export LD_LIBRARY_PATH=${TOOLROOT}/lib64:${TOOLROOT}/lib:${LD_LIBRARY_PATH:-}
unset CPATH CPLUS_INCLUDE_PATH C_INCLUDE_PATH INCLUDE LIBRARY_PATH
command -v python hipconfig hipcc rocminfo hy-smi gcc g++ > "${RUN}/prerequisites.txt"

stage=verify_pinned_inputs
test "$(sha256sum "${SOURCE_ARCHIVE}" | awk '{print $1}')" = 0ebbca14b5d5db9d236ed72e15fe6be9f97755136126d04196bfbc5130e77c6e
test "$(sha256sum "${CMAKE_ARCHIVE}" | awk '{print $1}')" = 5a1133ff103c71eb5120e2cc3de922733e7d8a26a98ae716397e8676adb367bf
ln "${SOURCE_ARCHIVE}" "${RUN}/llama-source.tar.gz"
ln "${CMAKE_ARCHIVE}" "${RUN}/cmake.tar.gz"
tar -xzf "${RUN}/llama-source.tar.gz" --strip-components=1 -C "${RUN}/src"
tar -xzf "${RUN}/cmake.tar.gz" -C "${RUN}"
CMAKE=${RUN}/cmake-3.31.6-linux-x86_64/bin/cmake
"${CMAKE}" --version | sed -n '1p' > "${RUN}/cmake-version.txt"
g++ --version | sed -n '1p' > "${RUN}/gcc-version.txt"

stage=verify_hip_version
hipconfig --version > "${RUN}/hip-version.txt"
python - "${RUN}/hip-version.txt" <<'PY'
import re, sys
text = open(sys.argv[1], errors="replace").read()
m = re.search(r"(\d+)\.(\d+)", text)
if not m or tuple(map(int, m.groups())) < (6, 1):
    raise SystemExit("Pinned source requires HIP >= 6.1; observed: " + text.strip())
PY

stage=discover_device_target
timeout 30 rocminfo > "${RUN}/rocminfo.txt" 2>&1
grep -Eo 'gfx[0-9a-z]+' "${RUN}/rocminfo.txt" | sort -u > "${RUN}/gpu-targets-all.txt"
test -s "${RUN}/gpu-targets-all.txt"
GPU_TARGET=$(sed -n '1p' "${RUN}/gpu-targets-all.txt")
printf '%s\n' "${GPU_TARGET}" > "${RUN}/gpu-target.txt"
hy-smi --showproductname > "${RUN}/hy-smi-product.txt" 2>&1 || true

stage=configure_hip_runtime
ROCM_PATH=$(hipconfig -R)
HIP_CLANG=$(hipconfig -l)/clang
test -x "${HIP_CLANG}"
export ROCM_PATH HIP_PATH=${ROCM_PATH} HIPCXX=${HIP_CLANG}
"${CMAKE}" -S "${RUN}/src" -B "${RUN}/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DGPU_TARGETS="${GPU_TARGET}" \
  -DGGML_NATIVE=OFF -DGGML_BLAS=OFF \
  -DCMAKE_C_COMPILER="${TOOLROOT}/bin/gcc" \
  -DCMAKE_CXX_COMPILER="${TOOLROOT}/bin/g++" \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF \
  -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_TOOLS=ON \
  > "${RUN}/configure.log" 2>&1
tail -200 "${RUN}/configure.log" > "${RUN}/configure-tail.txt"
grep -q 'HIP and hipBLAS found' "${RUN}/configure.log"

stage=build_hip_runtime
"${CMAKE}" --build "${RUN}/build" --config Release -j 8 --target llama-completion \
  > "${RUN}/build.log" 2>&1
tail -200 "${RUN}/build.log" > "${RUN}/build-tail.txt"
cp "${RUN}/build/bin/llama-completion" "${RUN}/llama-completion"
HIP_LIB=$(find "${RUN}/build" -type f -name 'libggml-hip.so*' -print -quit)
test -n "${HIP_LIB}"
cp "${HIP_LIB}" "${RUN}/libggml-hip.so"
ldd "${RUN}/llama-completion" > "${RUN}/runtime-ldd.txt"
grep -Ei 'ggml-hip|amdhip|hsa|hipblas|rocblas' "${RUN}/runtime-ldd.txt"

stage=verify_device_enumeration
timeout 60 "${RUN}/llama-completion" --list-devices > "${RUN}/device-enumeration.txt" 2>&1
grep -Ei 'HIP|DCU|Hygon|gfx' "${RUN}/device-enumeration.txt"

stage=complete
success=1
write_receipt BUILD_AND_DEVICE_ENUMERATION_PASS 0
trap - EXIT
