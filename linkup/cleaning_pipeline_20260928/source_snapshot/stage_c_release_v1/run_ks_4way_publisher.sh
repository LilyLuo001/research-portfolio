#!/bin/bash
set -euo pipefail
ROOT=/public/home/lilysharp
RELEASE=${ROOT}/linkup_analysis_v1/stage_c_release_v1
STATE=${ROOT}/linkup_release_v1/semantic_v1/kunshan
export PYTHONPATH=${ROOT}/linkup_analysis_v1/stage_b/runtime_py38
exec /public/software/apps/python/3.8.10/bin/python3 "${RELEASE}/login_transfer_worker.py" \
  --buffer-root "${STATE}/buffer" --buffer-subdirs ks_split0 ks_split1 ks_split2 ks_split3 \
  --checkpoint-root "${STATE}/checkpoints" --lock-name login-transfer-4way.lock \
  --status-name KS_4WAY_TRANSFER_WORKER_STATUS.json \
  --compute-complete-name REGION_PARTS_QUEUE_COMPLETE.json \
  --published-complete-name REGION_PUBLISHED_COMPLETE.ks_4way.json \
  --transfer "${RELEASE}/verified_transfer.py" \
  --host zzeshell.scnet.cn --port 65032 --user lilysharp \
  --key "${ROOT}/.ssh/hz_transfer_20260928" --known-hosts "${ROOT}/.ssh/hz_known_hosts_20260928" \
  --control-path '/tmp/linkup-hz-ks-4way-%r-%h-%p' \
  --remote-root /public/home/lilysharp/linkup_release_v1/full_semantic_v1 \
  --remote-cap-bytes 420000000000 --poll-seconds 20 --max-runtime-seconds 180000
