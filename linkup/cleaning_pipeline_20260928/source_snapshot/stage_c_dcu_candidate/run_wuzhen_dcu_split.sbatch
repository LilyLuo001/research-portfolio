#!/bin/bash
#SBATCH --job-name=linkup-semantic-wz-dcu-split
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH --output=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-dcu-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-dcu-%j.err
set -euo pipefail

ROOT=${RELEASE_ROOT:-/work/home/lilysharp/linkup_analysis_v1}
RELEASE=${ROOT}/stage_c_release_v1
CANDIDATE=${CANDIDATE_ROOT:-${ROOT}/stage_c_dcu_candidate}
SEMANTIC=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen
PARTITION_ID=${PARTITION_ID:?missing PARTITION_ID}
REMAINING_PLAN=${REMAINING_PLAN:?missing REMAINING_PLAN}
EXPECTED_PLAN_SHA256=${EXPECTED_PLAN_SHA256:?missing EXPECTED_PLAN_SHA256}
BUFFER_ROOT=${SEMANTIC}/buffer/${PARTITION_ID}
BUFFER_CAP_BYTES=3500000000
export LINKUP_DCU_EXECUTABLE=${CANDIDATE}/dcu_anchor_scan.single_owner_v2
export LINKUP_DCU_BATCH_ROWS=131072
export LINKUP_DCU_ARCH=gfx906
export LINKUP_DCU_SCAN_TIMEOUT_SECONDS=120
export LINKUP_DCU_LOCK_TIMEOUT_SECONDS=30
export LINKUP_DCU_LOCK_PATH=/tmp/linkup-dcu-${SLURM_JOB_ID}.lock
BUILD_RECEIPT=${SEMANTIC}/DCU_BUILD_PROVENANCE.single_owner_v2.json

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38:${CANDIDATE}

test -s "${REMAINING_PLAN}"
test "$(sha256sum "${REMAINING_PLAN}" | awk '{print $1}')" = "${EXPECTED_PLAN_SHA256}"
test -s "${BUILD_RECEIPT}"
test -x "${LINKUP_DCU_EXECUTABLE}"
for required in prepare_shard_input.py regional_runner.py enrichment.py; do
  test -r "${RELEASE}/${required}"
done
test "$(sha256sum "${CANDIDATE}/prefilter.py" | awk '{print $1}')" = 415c4a87b3ea61983b9588256a9e4348ce8f5f623c7771ef3c9e3101146d2835
test "$(sha256sum "${CANDIDATE}/candidate_adapter.py" | awk '{print $1}')" = e318932c69cd5d270def1ccc33134c3042e999f9cf0963afed1c0a8cdd42493b
test "$(sha256sum "${CANDIDATE}/dcu_anchor_scan.hip.cpp" | awk '{print $1}')" = c21cea4b8480a9f9acbc0f3656cfce3f3da6ae264b6ac1443fc2c13bd082d2f2
test "$(sha256sum "${CANDIDATE}/lean_writer_dcu.py" | awk '{print $1}')" = 6fc0be712aea0d22b667d5aba88bda5e1a66650a5654552051546758a7076983

if test -s "${BUILD_RECEIPT}"; then
  export LINKUP_DCU_EXECUTABLE_SHA256=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["executable_sha256"])' "${BUILD_RECEIPT}")
else
  /public/software/compiler/dtk-21.10/bin/hipcc -O3 -std=c++14 --offload-arch="${LINKUP_DCU_ARCH}" \
    "${CANDIDATE}/dcu_anchor_scan.hip.cpp" -o "${LINKUP_DCU_EXECUTABLE}.partial"
  chmod 700 "${LINKUP_DCU_EXECUTABLE}.partial"
  mv "${LINKUP_DCU_EXECUTABLE}.partial" "${LINKUP_DCU_EXECUTABLE}"
  export LINKUP_DCU_EXECUTABLE_SHA256=$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')
  python3 - "${BUILD_RECEIPT}" "${LINKUP_DCU_EXECUTABLE_SHA256}" <<'PY'
import json, os, sys
path, digest = sys.argv[1:]
value = {"status":"frozen", "architecture":"gfx906", "batch_rows":131072,
         "executable_sha256":digest,
         "prefilter_sha256":"415c4a87b3ea61983b9588256a9e4348ce8f5f623c7771ef3c9e3101146d2835",
         "adapter_sha256":"e318932c69cd5d270def1ccc33134c3042e999f9cf0963afed1c0a8cdd42493b",
         "hip_source_sha256":"c21cea4b8480a9f9acbc0f3656cfce3f3da6ae264b6ac1443fc2c13bd082d2f2"}
tmp=path+".tmp"; open(tmp,"w").write(json.dumps(value,indent=2,sort_keys=True)+"\n"); os.replace(tmp,path)
PY
fi
test -x "${LINKUP_DCU_EXECUTABLE}"
test "$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')" = "${LINKUP_DCU_EXECUTABLE_SHA256}"
/public/software/compiler/dtk-21.10/bin/hipconfig --version >&2
ldd "${LINKUP_DCU_EXECUTABLE}" >&2

FIRST_SHARD_ID=$(python3 -c 'import json,sys; print(json.loads(open(sys.argv[1]).readline())["shard_id"])' "${REMAINING_PLAN}")
FIRST_VALIDATED=${SEMANTIC}/DCU_FIRST_SHARD_VALIDATED.${PARTITION_ID}.json
FIRST_FAILED=${SEMANTIC}/DCU_FIRST_SHARD_FAILED.${PARTITION_ID}.json
MONITOR_LOG=${SEMANTIC}/dcu_runtime_monitor.${SLURM_JOB_ID}.csv
rm -f "${FIRST_FAILED}"

setsid python3 "${RELEASE}/regional_runner.py" \
  --transfer-mode queue --partition-id "${PARTITION_ID}" --plan "${REMAINING_PLAN}" \
  --buffer-root "${BUFFER_ROOT}" --checkpoint-root "${SEMANTIC}/checkpoints" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${RELEASE}/enrichment.py" --lean-writer "${CANDIDATE}/lean_writer_dcu.py" \
  --workers 32 --per-shard-output-cap-bytes 500000000 \
  --buffer-cap-bytes "${BUFFER_CAP_BYTES}" --free-reserve-bytes 8000000000 &
RUNNER_PID=$!

monitor_dcu() {
  echo 'epoch,gpu_busy_percent,vram_used_bytes,vram_total_bytes,power_microwatts,scanner_pid,render_device' > "${MONITOR_LOG}"
  while kill -0 "${RUNNER_PID}" 2>/dev/null; do
    scanner=$(pgrep -u "${USER}" -x dcu_anchor_scan | head -1 || true)
    render=''
    if test -n "${scanner}"; then
      for fd in /proc/${scanner}/fd/*; do
        target=$(readlink "${fd}" 2>/dev/null || true)
        case "${target}" in /dev/dri/renderD*) render=${target##*/}; break;; esac
      done
    fi
    if test -n "${render}" && test -r "/sys/class/drm/${render}/device/gpu_busy_percent"; then
      device=/sys/class/drm/${render}/device
      busy=$(cat "${device}/gpu_busy_percent")
      used=$(cat "${device}/mem_info_vram_used")
      total=$(cat "${device}/mem_info_vram_total")
      power=$(cat "${device}"/hwmon/hwmon*/power1_average 2>/dev/null | head -1 || true)
      echo "$(date +%s),${busy},${used},${total},${power:-},${scanner},${render}" >> "${MONITOR_LOG}"
    fi
    sleep 1
  done
}

watch_first_shard() {
  queued=${SEMANTIC}/checkpoints/${FIRST_SHARD_ID}.queued.json
  published=${SEMANTIC}/checkpoints/${FIRST_SHARD_ID}.published.json
  for unused in $(seq 1 180); do
    if test -s "${queued}" || test -s "${published}"; then
      python3 - "${queued}" "${published}" "${LINKUP_DCU_EXECUTABLE_SHA256}" \
        "${CANDIDATE}/lean_writer_dcu.py" "${FIRST_VALIDATED}" <<'PY'
import hashlib, json, os, sys, time
from pathlib import Path
queued, published, binary, writer, output = map(Path, sys.argv[1:])
binary = binary.name
for unused in range(20):
    if published.is_file():
        complete = json.loads(published.read_text())["shard_complete"]
        break
    if queued.is_file():
        receipt = json.loads(queued.read_text())
        path = Path(receipt["shard_complete"])
        if path.is_file():
            complete = json.loads(path.read_text())
            break
    time.sleep(.25)
else: raise RuntimeError("first shard receipt/output raced without a verifiable complete receipt")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert complete["code_sha256"]["lean_writer"] == sha(writer)
provenance = complete["lean_complete"]["dcu_provenance"]
assert provenance["backend"] == "hip" and provenance["executable_sha256"] == binary
value = {"status":"validated", "at":time.time(), "code_sha256":complete["code_sha256"],
         "dcu_provenance":provenance, "processed_rows":complete["lean_complete"]["processed_rows"]}
temp=Path(str(output)+".tmp"); temp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n"); os.replace(temp,output)
PY
      return
    fi
    kill -0 "${RUNNER_PID}" 2>/dev/null || return
    sleep 5
  done
  cat > "${FIRST_FAILED}.tmp" <<EOF
{"status":"first_shard_timeout","timeout_seconds":900,"runner_pid":${RUNNER_PID},"generated_output_retained":true}
EOF
  mv "${FIRST_FAILED}.tmp" "${FIRST_FAILED}"
  kill -TERM -- "-${RUNNER_PID}" 2>/dev/null || true
}

monitor_dcu & MONITOR_PID=$!
watch_first_shard & WATCHDOG_PID=$!
set +e
wait "${RUNNER_PID}"; RUNNER_RC=$?
set -e
kill "${MONITOR_PID}" "${WATCHDOG_PID}" 2>/dev/null || true
wait "${MONITOR_PID}" "${WATCHDOG_PID}" 2>/dev/null || true
test ! -e "${FIRST_FAILED}" || exit 75
test "${RUNNER_RC}" -eq 0 || exit "${RUNNER_RC}"
test -s "${FIRST_VALIDATED}"
