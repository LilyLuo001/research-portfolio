#!/bin/bash
#SBATCH --job-name=linkup-narrow
#SBATCH --partition=hx1hdnormal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=dcu:1
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/semantic-narrow-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/semantic-narrow-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load anaconda3/2023.09
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 ARROW_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=${ROOT}/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json
CUTOFF_EPOCH=$(date -d '2026-10-07 18:00:00 +0800' +%s)
test "$(date +%s)" -lt "${CUTOFF_EPOCH}"
python "${ROOT}/code/pre_revelio_execution_v1/run_semantic_narrow_batch.py" \
  --gate "${GATE}" \
  --plans "${ROOT}/private/gate_v2_20261003/plans/kunshan.plan.jsonl" "${ROOT}/private/gate_v2_20261003/plans/wuzhen.plan.jsonl" \
  --manifest "${ROOT}/private/full_manifest_v2.jsonl" \
  --work-dir "${ROOT}/private/semantic_narrow_v1" \
  --builder "${ROOT}/code/pre_revelio_execution_v1/build_semantic_narrow.py" \
  --workers 8
