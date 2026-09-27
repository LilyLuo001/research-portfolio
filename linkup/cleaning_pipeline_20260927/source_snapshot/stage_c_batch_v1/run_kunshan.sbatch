#!/bin/bash
#SBATCH --job-name=linkup_v4_bound_ks
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_batch_v1/logs/batch-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_batch_v1/logs/batch-%j.err
set -euo pipefail

module load python/3.8.10
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38

ROOT=/public/home/lilysharp/linkup_analysis_v1
RUNNER=${ROOT}/stage_c_batch_v1/bounded_candidate_batch.py
MANIFEST=/public/home/lilysharp/linkup_audit_20260927/description_regions_disjoint_manifest.json
PARSER=${ROOT}/stage_c_v4/requirement_candidates.py
OUT=${ROOT}/stage_c_batch_v1/outputs/kunshan_bounded_v1

quota -s || true
du -sb "${ROOT}" || true
python3 -c 'import pyarrow; print("python", __import__("sys").version); print("pyarrow", pyarrow.__version__)'
test "${LINKUP_CONFIRMED_HEADROOM_BYTES:-0}" -ge 300000000 || {
  echo "Set LINKUP_CONFIRMED_HEADROOM_BYTES from the user quota reading (not df); need >=300000000." >&2
  exit 64
}

python3 "${RUNNER}" \
  --region kunshan --manifest "${MANIFEST}" --parser "${PARSER}" --output-dir "${OUT}" \
  --file-count 4 --rows-per-file 4000 --batch-size 256 --workers 4 \
  --output-cap-bytes 250000000 --confirmed-headroom-bytes "${LINKUP_CONFIRMED_HEADROOM_BYTES}"
