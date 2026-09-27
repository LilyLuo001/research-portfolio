#!/bin/bash
#SBATCH --job-name=linkup_v4_bound_wz
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --gres=dcu:Hygon:1
#SBATCH --output=/work/home/lilysharp/linkup_analysis_v1/stage_c_batch_v1/logs/batch-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_analysis_v1/stage_c_batch_v1/logs/batch-%j.err
set -euo pipefail

module load python/3.8.10
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

ROOT=/work/home/lilysharp/linkup_analysis_v1
RUNNER=${ROOT}/stage_c_batch_v1/bounded_candidate_batch.py
MANIFEST=${ROOT}/audit_20260927/description_regions_disjoint_manifest.json
PARSER=${ROOT}/stage_c_v4/requirement_candidates.py
OUT=${ROOT}/stage_c_batch_v1/outputs/wuzhen_bounded_v1

# Read-only dependency discovery.  Do not pip/conda install on this job.
if python3 -c 'import pyarrow' 2>/dev/null; then
  :
elif test -n "${WUZHEN_PYARROW_PATH:-}" && PYTHONPATH="${WUZHEN_PYARROW_PATH}" python3 -c 'import pyarrow' 2>/dev/null; then
  export PYTHONPATH="${WUZHEN_PYARROW_PATH}"
else
  echo "PyArrow for module python/3.8.10 is missing or undiscovered; set read-only WUZHEN_PYARROW_PATH. No install attempted." >&2
  exit 65
fi

quota -s || true
du -sb "${ROOT}" || true
python3 -c 'import pyarrow; print("python", __import__("sys").version); print("pyarrow", pyarrow.__version__)'
test "${LINKUP_CONFIRMED_HEADROOM_BYTES:-0}" -ge 300000000 || {
  echo "Set LINKUP_CONFIRMED_HEADROOM_BYTES from the user quota reading (not df); need >=300000000." >&2
  exit 64
}

python3 "${RUNNER}" \
  --region wuzhen --manifest "${MANIFEST}" --parser "${PARSER}" --output-dir "${OUT}" \
  --file-count 4 --rows-per-file 4000 --batch-size 256 --workers 4 \
  --output-cap-bytes 250000000 --confirmed-headroom-bytes "${LINKUP_CONFIRMED_HEADROOM_BYTES}"
