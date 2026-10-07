#!/bin/bash
#SBATCH --job-name=linkup-text10k-wz
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=10G
#SBATCH --time=04:00:00
#SBATCH --output=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/run-123660254/logs/wuzhen-%j.out
#SBATCH --error=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/run-123660254/logs/wuzhen-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
RUN=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/run-123660254
CODE=/work/home/lilysharp/private/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007
umask 077
python3 "${CODE}/materialize_fixed10000_selected_text.py" \
  --selection "${RUN}/fixed10000_wuzhen.selection.json" \
  --source-map "${RUN}/fixed10000_wuzhen.source_map.jsonl" \
  --output "${RUN}/fixed10000_wuzhen.text.csv" \
  --receipt "${RUN}/fixed10000_wuzhen.materialize_receipt.json" \
  --text-column DESCRIPTION --max-rows 10000
