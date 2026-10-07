#!/bin/bash
#SBATCH --job-name=linkup-text10k-ksh
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=10G
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/text_handoff_20261007/run-123660254/logs/kunshan-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/text_handoff_20261007/run-123660254/logs/kunshan-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
RUN=/public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/text_handoff_20261007/run-123660254
CODE=/public/home/lilysharp/linkup_analysis_execution_oct02/code/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007
umask 077
python3 "${CODE}/materialize_fixed10000_selected_text.py" \
  --selection "${RUN}/fixed10000_kunshan.selection.json" \
  --source-map "${RUN}/fixed10000_kunshan.source_map.jsonl" \
  --output "${RUN}/fixed10000_kunshan.text.csv" \
  --receipt "${RUN}/fixed10000_kunshan.materialize_receipt.json" \
  --text-column DESCRIPTION --max-rows 10000
