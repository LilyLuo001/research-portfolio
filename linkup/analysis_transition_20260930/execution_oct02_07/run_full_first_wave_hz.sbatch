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
source /etc/profile.d/modules.sh
module load anaconda3/2023.09
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
GATE=${ROOT}/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json
test -f "${GATE}"
test "$(wc -l < "${ROOT}/private/full_manifest_v2.jsonl")" -eq 2464
python "${ROOT}/code/run_first_wave.py" --gate "${GATE}" --plans "${ROOT}/private/gate_v2_20261003/plans/kunshan.plan.jsonl" "${ROOT}/private/gate_v2_20261003/plans/wuzhen.plan.jsonl" \
  --manifest "${ROOT}/private/full_manifest_v2.jsonl" --work-dir "${ROOT}/results/full_first_wave_v2" --workers 8 \
  --builder "${ROOT}/code/build_release_first_tables.py"
