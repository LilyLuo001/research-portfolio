#!/bin/bash
# Region-specific copies must set partition, memory, optional Wuzhen GRES, and paths.
# Do not add --exclusive.
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

python3 "${RELEASE_ROOT}/regional_runner.py" \
  --plan "${REGION_PLAN}" --buffer-root "${BUFFER_ROOT}" \
  --checkpoint-root "${CHECKPOINT_ROOT}" \
  --parser "${RELEASE_ROOT}/../stage_c_v6/requirement_candidates.py" \
  --enrichment "${RELEASE_ROOT}/enrichment.py" \
  --lean-writer "${RELEASE_ROOT}/lean_writer.py" \
  --transfer "${RELEASE_ROOT}/verified_transfer.py" \
  --workers 32 --per-shard-output-cap-bytes "${PER_SHARD_OUTPUT_CAP_BYTES}" \
  --buffer-cap-bytes "${BUFFER_CAP_BYTES}" --free-reserve-bytes "${FREE_RESERVE_BYTES}" \
  --transfer-host zzeshell.scnet.cn --transfer-port 65032 \
  --transfer-user lilysharp --transfer-key "${HZ_TRANSFER_KEY}" \
  --transfer-known-hosts "${HZ_KNOWN_HOSTS}" \
  --transfer-control-path "${HZ_CONTROL_PATH}" \
  --remote-root "${HZ_REMOTE_ROOT}" \
  --remote-cap-bytes 420000000000 --transfer-attempts 3
