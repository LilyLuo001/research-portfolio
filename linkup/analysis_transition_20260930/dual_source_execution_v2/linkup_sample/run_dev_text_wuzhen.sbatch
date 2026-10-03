#!/bin/bash
#SBATCH --job-name=linkup-devtext-wz-v2
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/dual_source_execution_v2/linkup_sample/run-123584403/logs/devtext-wz-%j.out
#SBATCH --error=/work/home/lilysharp/private/dual_source_execution_v2/linkup_sample/run-123584403/logs/devtext-wz-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
RUN=/work/home/lilysharp/private/dual_source_execution_v2/linkup_sample/run-123584403/dev_text_adapter
python3 /work/home/lilysharp/private/human_review_pack_20261003/phase2_tools/materialize_selected_text.py \
  --selection "${RUN}/development_200_wuzhen.selection.json" \
  --source-map "${RUN}/development_200_wuzhen.source_map.jsonl" \
  --output "${RUN}/development_200_wuzhen.text.csv" \
  --receipt "${RUN}/development_200_wuzhen.materialize_receipt.json" \
  --text-column DESCRIPTION --max-rows 200
