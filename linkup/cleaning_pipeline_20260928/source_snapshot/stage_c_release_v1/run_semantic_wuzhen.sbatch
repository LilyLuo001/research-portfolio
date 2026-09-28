#!/bin/bash
#SBATCH --job-name=linkup-semantic-wz
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH --output=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen/logs/compute-%j.err
set -euo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
R=/work/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
S=/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen
python3 "${R}/regional_runner.py" \
  --transfer-mode queue --plan "${S}/plan.jsonl" --buffer-root "${S}/buffer" \
  --checkpoint-root "${S}/checkpoints" --parser /work/home/lilysharp/linkup_analysis_v1/stage_c_v6/requirement_candidates.py \
  --enrichment "${R}/enrichment.py" --lean-writer "${R}/lean_writer.py" --workers 32 \
  --per-shard-output-cap-bytes 500000000 --buffer-cap-bytes 8000000000 --free-reserve-bytes 8000000000
