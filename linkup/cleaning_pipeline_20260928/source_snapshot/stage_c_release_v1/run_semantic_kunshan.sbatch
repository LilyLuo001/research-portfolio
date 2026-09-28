#!/bin/bash
#SBATCH --job-name=linkup-semantic-ks
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=2-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan/logs/compute-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan/logs/compute-%j.err
set -euo pipefail
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
R=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
S=/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan
/public/software/apps/python/3.8.10/bin/python3 "${R}/regional_runner.py" \
  --transfer-mode queue --plan "${S}/plan.jsonl" --buffer-root "${S}/buffer" \
  --checkpoint-root "${S}/checkpoints" --parser /public/home/lilysharp/linkup_analysis_v1/stage_c_v6/requirement_candidates.py \
  --enrichment "${R}/enrichment.py" --lean-writer "${R}/lean_writer.py" --workers 32 \
  --per-shard-output-cap-bytes 500000000 --buffer-cap-bytes 4000000000 --free-reserve-bytes 8000000000
