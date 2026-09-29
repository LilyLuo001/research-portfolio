#!/bin/bash
#SBATCH --job-name=linkup-semantic-wz-dcu-pilot
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/dcu-v2-diagnostic-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/dcu-v2-diagnostic-%j.err
set -euo pipefail

: "${PILOT_SOURCE:?set one representative staged canonical-USA parquet}"
: "${PILOT_OUTPUT:?set a new empty output directory}"
ROOT=${RELEASE_ROOT:-/work/home/lilysharp/linkup_analysis_v1}
CANDIDATE=${CANDIDATE_ROOT:-${ROOT}/stage_c_dcu_candidate}
export LINKUP_DCU_EXECUTABLE=${TMPDIR:-/tmp}/dcu_anchor_scan.single_owner_v2.${SLURM_JOB_ID}
export LINKUP_DCU_BATCH_ROWS=131072
export LINKUP_DCU_ARCH=gfx906
export LINKUP_DCU_SCAN_TIMEOUT_SECONDS=120
export LINKUP_DCU_LOCK_TIMEOUT_SECONDS=30
export LINKUP_DCU_LOCK_PATH=/tmp/linkup-dcu-${SLURM_JOB_ID}.lock

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38:${CANDIDATE}

test "$(sha256sum "${CANDIDATE}/prefilter.py" | awk '{print $1}')" = 6f3088165cdd7afcf0a340174785982f5fea0a2225267a3b885d7b5c63348d49
test "$(sha256sum "${CANDIDATE}/candidate_adapter.py" | awk '{print $1}')" = e318932c69cd5d270def1ccc33134c3042e999f9cf0963afed1c0a8cdd42493b
test "$(sha256sum "${CANDIDATE}/dcu_anchor_scan.hip.cpp" | awk '{print $1}')" = a2c68343f0d43af93df8a3c1ffcf640ccf23a591606bef47f99644c374c697b3
test "$(sha256sum "${CANDIDATE}/lean_writer_dcu.py" | awk '{print $1}')" = 4e25658c576496ec9f50c430034d0a9a9df623601b514bf105ee78e6dca5fc7e
/public/software/compiler/dtk-21.10/bin/hipconfig --version >&2
/public/software/compiler/dtk-21.10/bin/hipcc -O3 -std=c++14 --offload-arch=gfx906 \
  "${CANDIDATE}/dcu_anchor_scan.hip.cpp" -o "${LINKUP_DCU_EXECUTABLE}"
chmod 700 "${LINKUP_DCU_EXECUTABLE}"
export LINKUP_DCU_EXECUTABLE_SHA256=$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')
test -x "${LINKUP_DCU_EXECUTABLE}"
test "$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')" = "${LINKUP_DCU_EXECUTABLE_SHA256}"
ldd "${LINKUP_DCU_EXECUTABLE}" >&2
python3 "${CANDIDATE}/lean_writer_dcu.py" \
  --source "${PILOT_SOURCE}" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${ROOT}/stage_c_release_v1/enrichment.py" \
  --output-dir "${PILOT_OUTPUT}" --workers 32 --output-cap-bytes 500000000

python3 - "${PILOT_SOURCE}" "${PILOT_OUTPUT}/COMPLETE.json" "${LINKUP_DCU_EXECUTABLE_SHA256}" <<'PY'
import json, sys
import pyarrow.parquet as pq
source, receipt, executable = sys.argv[1:]
value = json.load(open(receipt))
assert value["status"] == "complete"
assert value["processed_rows"] == pq.ParquetFile(source).metadata.num_rows
assert value["dcu_provenance"]["executable_sha256"] == executable
assert value["dcu_provenance"]["backend"] == "hip"
assert set(value["schemas"]) == {"ad_status", "experience", "technology", "v6_audit"}
print("DIAGNOSTIC_OUTPUT_VALID rows=%d executable_sha256=%s" %
      (value["processed_rows"], executable))
PY
