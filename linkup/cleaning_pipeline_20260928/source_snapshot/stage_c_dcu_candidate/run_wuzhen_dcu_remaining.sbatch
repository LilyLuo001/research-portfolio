#!/bin/bash
#SBATCH --job-name=linkup-semantic-wz-dcu-r1
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=2-00:00:00
#SBATCH --output=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-dcu-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-dcu-%j.err
set -euo pipefail

ROOT=${RELEASE_ROOT:-/work/home/lilysharp/linkup_analysis_v1}
RELEASE=${ROOT}/stage_c_release_v1
CANDIDATE=${CANDIDATE_ROOT:-${ROOT}/stage_c_dcu_candidate}
SEMANTIC=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen
REMAINING_PLAN=${REMAINING_PLAN:-${SEMANTIC}/plan.dcu_remaining.jsonl}
export LINKUP_DCU_EXECUTABLE=${CANDIDATE}/dcu_anchor_scan
export LINKUP_DCU_BATCH_ROWS=4096
export LINKUP_DCU_ARCH=gfx906
BUILD_RECEIPT=${SEMANTIC}/DCU_BUILD_PROVENANCE.json

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38:${CANDIDATE}

test -s "${REMAINING_PLAN}"
for required in prepare_shard_input.py regional_runner.py enrichment.py; do
  test -r "${RELEASE}/${required}"
done
test "$(sha256sum "${CANDIDATE}/prefilter.py" | awk '{print $1}')" = a884fb426d9269c480e1ab1e5760601412fa436573022c51f6fe5812dbca2803
test "$(sha256sum "${CANDIDATE}/candidate_adapter.py" | awk '{print $1}')" = f83c13d084e19e762a5f71b1441b1610f8de983664feb75c03ad8e404a53909a
test "$(sha256sum "${CANDIDATE}/dcu_anchor_scan.hip.cpp" | awk '{print $1}')" = 54a804af0ae59db2aadbd8cb50f71935ed725b47d1b1980eeabfa890add58488
test "$(sha256sum "${CANDIDATE}/lean_writer_dcu.py" | awk '{print $1}')" = 16ebbab4ed7e7db6dd04ade19d9b8b8bd1b62d1b053b51ce63ee53fdedef3665

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
value = {"status":"frozen", "architecture":"gfx906", "batch_rows":4096,
         "executable_sha256":digest,
         "prefilter_sha256":"a884fb426d9269c480e1ab1e5760601412fa436573022c51f6fe5812dbca2803",
         "adapter_sha256":"f83c13d084e19e762a5f71b1441b1610f8de983664feb75c03ad8e404a53909a",
         "hip_source_sha256":"54a804af0ae59db2aadbd8cb50f71935ed725b47d1b1980eeabfa890add58488"}
tmp=path+".tmp"; open(tmp,"w").write(json.dumps(value,indent=2,sort_keys=True)+"\n"); os.replace(tmp,path)
PY
fi
test -x "${LINKUP_DCU_EXECUTABLE}"
test "$(sha256sum "${LINKUP_DCU_EXECUTABLE}" | awk '{print $1}')" = "${LINKUP_DCU_EXECUTABLE_SHA256}"

python3 "${RELEASE}/regional_runner.py" \
  --transfer-mode queue --partition-id dcu_remaining --plan "${REMAINING_PLAN}" \
  --buffer-root "${SEMANTIC}/buffer" --checkpoint-root "${SEMANTIC}/checkpoints" \
  --parser "${ROOT}/stage_c_v6/requirement_candidates.py" \
  --enrichment "${RELEASE}/enrichment.py" --lean-writer "${CANDIDATE}/lean_writer_dcu.py" \
  --workers 8 --per-shard-output-cap-bytes 500000000 \
  --buffer-cap-bytes 8000000000 --free-reserve-bytes 8000000000

python3 - "${SEMANTIC}" "${RELEASE}" "${CANDIDATE}" "${LINKUP_DCU_EXECUTABLE_SHA256}" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
s, r, c, binary = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,v):
 t=Path(str(p)+".tmp"); t.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n"); os.replace(t,p)
atomic(s/"WZ_OLD_CODE.json", {"parser":"d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744","enrichment":"cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6","lean_writer":"67c22e5db1d61f7a909235150a0254f9af9bd2ccd6f1958aa6d7a555e32b99d5"})
atomic(s/"WZ_NEW_CODE.json", {"parser":sha(r.parent/"stage_c_v6"/"requirement_candidates.py"),"enrichment":sha(r/"enrichment.py"),"lean_writer":sha(c/"lean_writer_dcu.py")})
atomic(s/"WZ_NEW_DCU_PROVENANCE.json", {"backend":"hip","architecture":"gfx906","batch_rows":4096,"prefilter_sha256":"a884fb426d9269c480e1ab1e5760601412fa436573022c51f6fe5812dbca2803","adapter_sha256":"f83c13d084e19e762a5f71b1441b1610f8de983664feb75c03ad8e404a53909a","hip_source_sha256":"54a804af0ae59db2aadbd8cb50f71935ed725b47d1b1980eeabfa890add58488","executable_sha256":binary,"frozen_v6_sha256":"d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744","frozen_v5_sha256":"336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd","frozen_enrichment_sha256":"cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6"})
PY

python3 "${RELEASE}/wz_mixed_completion_gate.py" \
  --full-plan "${SEMANTIC}/plan.jsonl" --new-plan "${REMAINING_PLAN}" \
  --checkpoint-root "${SEMANTIC}/checkpoints" \
  --old-code "${SEMANTIC}/WZ_OLD_CODE.json" --new-code "${SEMANTIC}/WZ_NEW_CODE.json" \
  --new-provenance "${SEMANTIC}/WZ_NEW_DCU_PROVENANCE.json"
