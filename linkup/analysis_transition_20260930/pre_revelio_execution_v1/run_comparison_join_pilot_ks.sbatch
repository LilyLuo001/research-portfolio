#!/bin/bash
#SBATCH --job-name=linkup-c1c2-pilot
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/comparison-pilot-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/comparison-pilot-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
PILOT=${ROOT}/private/semantic_narrow_validation_v2
RECEIPT=$(find "${PILOT}" -maxdepth 1 -type f -name '*.receipt.json' -print -quit)
test -n "${RECEIPT}"
python "${ROOT}/code/pre_revelio_execution_v1/build_comparison_join.py" \
  --narrow-dir "${PILOT}" --narrow-batch-receipt "${RECEIPT}" \
  --source-manifest "${ROOT}/private/full_manifest_v2.jsonl" \
  --records-root /public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1 \
  --onet-glob '/public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables/onet-taxonomy/*.parquet' \
  --official-codes "${ROOT}/private/official_onet2019_occupations.csv" \
  --work-dir "${ROOT}/private/comparison_join_pilot_v1" --threads 8 --memory-limit 12GB --expected-shards 1
python "${ROOT}/code/pre_revelio_execution_v1/build_fixed_comparisons.py" \
  --input "${ROOT}/private/comparison_join_pilot_v1/joined" \
  --join-manifest "${ROOT}/private/comparison_join_pilot_v1/JOIN_MANIFEST.json" \
  --output-dir "${ROOT}/results/T5_T6_pilot_v1"
