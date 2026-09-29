#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
set -euo pipefail
PARTITION_ID=${PARTITION_ID:?missing PARTITION_ID}
PLAN=${PLAN:?missing PLAN}
EXPECTED_PLAN_SHA256=${EXPECTED_PLAN_SHA256:?missing EXPECTED_PLAN_SHA256}
ROOT=/public/home/lilysharp/linkup_analysis_v1
RELEASE=${ROOT}/stage_c_release_v1
STATE=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan
export PYTHONPATH=${ROOT}/stage_b/runtime_py38
test "$(sha256sum "${PLAN}" | awk '{print $1}')" = "${EXPECTED_PLAN_SHA256}"
for required in prepare_shard_input.py regional_runner.py enrichment.py lean_writer.py; do
  test -r "${RELEASE}/${required}" || { echo "missing release dependency: ${required}" >&2; exit 2; }
done
/public/software/apps/python/3.8.10/bin/python3 "${RELEASE}/regional_runner.py" \
  --transfer-mode queue --partition-id "${PARTITION_ID}" --plan "${PLAN}" \
  --buffer-root "${STATE}/buffer/${PARTITION_ID}" --checkpoint-root "${STATE}/checkpoints" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${RELEASE}/enrichment.py" --lean-writer "${RELEASE}/lean_writer.py" \
  --workers 32 --per-shard-output-cap-bytes 500000000 \
  --per-shard-buffer-reserve-bytes 750000000 --buffer-cap-bytes 1000000000 \
  --free-reserve-bytes 8000000000
