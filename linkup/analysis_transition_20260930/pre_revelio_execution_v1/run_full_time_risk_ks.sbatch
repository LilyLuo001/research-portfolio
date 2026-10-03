#!/bin/bash
# Production annual-resume launcher.  The builder verifies and binds the
# completed 16-prefix v3 outputs without rewriting their source receipts, then
# runs the fixed-prefix-0 annual diagnostic in the same audited work directory.
# Validated builder sha256: d496082d841a2f75b576058d2df252dd8f28c526d1f61596e0267832b22e6064
#SBATCH --job-name=linkup-t4-full
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/t4-full-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_execution_oct02/logs/t4-full-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_analysis_execution_oct02
python "${ROOT}/code/pre_revelio_execution_v1/build_full_time_risk.py" \
  --narrow-dir "${ROOT}/private/semantic_narrow_v1/shards" \
  --narrow-batch-receipt "${ROOT}/private/semantic_narrow_v1/BATCH_RECEIPT.json" \
  --global-key-audit "${ROOT}/private/comparison_join_v1/GLOBAL_JOB_HASH_AUDIT.json" \
  --global-key-dir "${ROOT}/private/comparison_join_v1/global_job_hash_keys" \
  --duplicate-dir "${ROOT}/private/comparison_join_v1/duplicate_job_hashes" \
  --records-index-root /public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1 \
  --raw-records-glob '/public/home/lilysharp/dewey_downloads/data/linkup_job_records/*.parquet' \
  --onet-glob '/public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables/onet-taxonomy/*.parquet' \
  --official-codes "${ROOT}/private/official_onet2019_occupations.csv" \
  --work-dir "${ROOT}/private/full_time_risk_v3" \
  --output-dir "${ROOT}/results/T4_full_v3" --threads 8 --memory-limit 12GB
