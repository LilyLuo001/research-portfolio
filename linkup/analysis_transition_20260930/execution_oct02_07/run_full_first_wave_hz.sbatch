#!/bin/bash
#SBATCH --job-name=linkup-first-wave
#SBATCH --partition=hx1hdnormal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=dcu:1
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/full-first-wave-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/full-first-wave-%j.err
set -euo pipefail
module load anaconda3/2023.09
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=/public/home/lilysharp/linkup_release_v1/full_semantic_v1/ALL_REGIONS_VERIFIED_COMPLETE.json
test -f "${GATE}"
python "${ROOT}/code/prepare_full_hz_manifest.py" --plans "${ROOT}/private/kunshan.plan.jsonl" "${ROOT}/private/wuzhen.plan.jsonl" \
  --sink /public/home/lilysharp/linkup_release_v1/full_semantic_v1 --receipts "${ROOT}/private/published_receipts" \
  --output "${ROOT}/private/full_manifest.jsonl"
python "${ROOT}/code/run_first_wave.py" --gate "${GATE}" --plans "${ROOT}/private/kunshan.plan.jsonl" "${ROOT}/private/wuzhen.plan.jsonl" \
  --manifest "${ROOT}/private/full_manifest.jsonl" --work-dir "${ROOT}/results/full_first_wave_v1" --workers 8 \
  --builder "${ROOT}/code/build_release_first_tables.py"
