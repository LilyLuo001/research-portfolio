#!/bin/bash
set -euo pipefail
REGION=${1:?usage: run_login_transfer_worker.sh kunshan|wuzhen}
CONTROL_TAG=${REGION}
case "${REGION}" in
  kunshan)
    HOME_ROOT=/public/home/lilysharp
    RUNTIME=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
    PYTHON_BIN=/public/software/apps/python/3.8.10/bin/python3
    BUFFER_ARGS=(--buffer-subdirs part0 part1 --lock-name login-transfer-partitions.lock \
      --status-name PARTITION_TRANSFER_WORKER_STATUS.json \
      --compute-complete-name REGION_PARTS_QUEUE_COMPLETE.json)
    ;;
  wuzhen)
    HOME_ROOT=/work/home/lilysharp
    RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
    set +u
    source /etc/profile >/dev/null 2>&1 || true
    module load python/3.8.10
    source /work/home/lilysharp/proxy.sh >/dev/null 2>&1
    set -u
    CONTROL_TAG=wuzhen-proxy
    PYTHON_BIN=$(command -v python3)
    BUFFER_ARGS=()
    ;;
  *) echo "invalid region" >&2; exit 2 ;;
esac
RELEASE=${HOME_ROOT}/linkup_analysis_v1/stage_c_release_v1
STATE=${HOME_ROOT}/linkup_release_v1/semantic_v1/${REGION}
mkdir -p "${STATE}/buffer" "${STATE}/checkpoints" "${STATE}/logs"
export PYTHONPATH=${RUNTIME}
# Bash 4.2 treats an empty array expansion as unbound under `set -u`.
set +u
exec "${PYTHON_BIN}" "${RELEASE}/login_transfer_worker.py" \
  --buffer-root "${STATE}/buffer" --checkpoint-root "${STATE}/checkpoints" \
  "${BUFFER_ARGS[@]}" \
  --transfer "${RELEASE}/verified_transfer.py" \
  --host zzeshell.scnet.cn --port 65032 --user lilysharp \
  --key "${HOME_ROOT}/.ssh/hz_transfer_20260928" \
  --known-hosts "${HOME_ROOT}/.ssh/hz_known_hosts_20260928" \
  --control-path "/tmp/linkup-hz-${CONTROL_TAG}-%r-%h-%p" \
  --remote-root /public/home/lilysharp/linkup_release_v1/full_semantic_v1 \
  --remote-cap-bytes 420000000000 --poll-seconds 20 --max-runtime-seconds 180000
