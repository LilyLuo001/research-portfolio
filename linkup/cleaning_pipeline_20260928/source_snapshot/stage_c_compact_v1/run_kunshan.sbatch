#!/bin/bash
#SBATCH --job-name=linkup_v5_compact
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_compact_v1/logs/compact-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_compact_v1/logs/compact-%j.err
set -euo pipefail
module load python/3.8.10
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_analysis_v1
test "${LINKUP_CONFIRMED_HEADROOM_BYTES:-0}" -ge 300000000
python3 "${ROOT}/stage_c_compact_v1/compact_candidate_batch.py" batch \
  --region kunshan --manifest /public/home/lilysharp/linkup_audit_20260927/description_regions_disjoint_manifest.json \
  --parser "${ROOT}/stage_c_v5/requirement_candidates.py" \
  --output-dir "${ROOT}/stage_c_compact_v1/outputs/kunshan_bounded_v1" \
  --file-count 4 --rows-per-file 4000 --batch-size 256 --workers 4 \
  --output-cap-bytes 250000000 --confirmed-headroom-bytes "${LINKUP_CONFIRMED_HEADROOM_BYTES}"
