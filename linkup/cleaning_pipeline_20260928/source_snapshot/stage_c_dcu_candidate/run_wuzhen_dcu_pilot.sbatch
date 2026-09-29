#!/bin/bash
#SBATCH --job-name=linkup-semantic-wz-dcu-pilot
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=00:30:00
set -euo pipefail

: "${PILOT_SOURCE:?set one representative staged canonical-USA parquet}"
: "${PILOT_OUTPUT:?set a new empty output directory}"
ROOT=${RELEASE_ROOT:-/work/home/lilysharp/linkup_analysis_v1}
CANDIDATE=${CANDIDATE_ROOT:-${ROOT}/stage_c_dcu_candidate}
export LINKUP_DCU_EXECUTABLE=${CANDIDATE}/dcu_anchor_scan
export LINKUP_DCU_BATCH_ROWS=${LINKUP_DCU_BATCH_ROWS:-4096}
export LINKUP_DCU_ARCH=${LINKUP_DCU_ARCH:-gfx906}
: "${LINKUP_DCU_EXECUTABLE_SHA256:?set to sha256sum of the compiled scanner}"
export LINKUP_DCU_EXECUTABLE_SHA256

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38:${CANDIDATE}

test -x "${LINKUP_DCU_EXECUTABLE}"
test "$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')" = "${LINKUP_DCU_EXECUTABLE_SHA256}"
python3 "${CANDIDATE}/lean_writer_dcu.py" \
  --source "${PILOT_SOURCE}" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${ROOT}/stage_c_release_v1/enrichment.py" \
  --output-dir "${PILOT_OUTPUT}" --workers 32 --output-cap-bytes 500000000
