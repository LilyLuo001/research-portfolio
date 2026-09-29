#!/bin/bash
set -euo pipefail
HOME_ROOT=/work/home/lilysharp
RELEASE=${HOME_ROOT}/linkup_analysis_v1/stage_c_release_v1
STATE=${HOME_ROOT}/linkup_release_v1/semantic_v1/wuzhen
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
source ${HOME_ROOT}/proxy.sh >/dev/null 2>&1
set -u
export PYTHONPATH=${HOME_ROOT}/linkup_release_v1/runtime_py38
exec python3 "${RELEASE}/login_transfer_worker.py" \
  --buffer-root "${STATE}/buffer" --buffer-subdirs dcu_part0 dcu_part1 \
  --checkpoint-root "${STATE}/checkpoints" \
  --lock-name login-transfer-dcu-split.lock \
  --status-name DCU_SPLIT_TRANSFER_WORKER_STATUS.json \
  --compute-complete-name REGION_QUEUE_COMPLETE.json \
  --published-complete-name REGION_PUBLISHED_COMPLETE.dcu_split.json \
  --transfer "${RELEASE}/verified_transfer.py" \
  --host zzeshell.scnet.cn --port 65032 --user lilysharp \
  --key "${HOME_ROOT}/.ssh/hz_transfer_20260928" \
  --known-hosts "${HOME_ROOT}/.ssh/hz_known_hosts_20260928" \
  --control-path "/tmp/linkup-hz-wuzhen-dcu-split-%r-%h-%p" \
  --remote-root /public/home/lilysharp/linkup_release_v1/full_semantic_v1 \
  --remote-cap-bytes 420000000000 --poll-seconds 20 --max-runtime-seconds 180000
