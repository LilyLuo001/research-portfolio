#!/bin/bash
#SBATCH --job-name=lk-pro-root009
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/checkpoint-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/checkpoint-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_corpus_pro_review_20261026/runtime_existing/runtime_jsonschema:/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2

R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
O="$R/root_batch009_validation/$SLURM_JOB_ID"
mkdir -p "$O/private" "$O/public"
result=0
for i in 0001 0002 0003 0004 0005 0006; do
  python "$R/code/validate_reviews.py" --packet "$R/batch009/private/packet_${i}.jsonl" --reviews "$R/reviews_private/batch009_packet_${i}_PRIMARY.jsonl" --schema "$R/code/FORMAL800_REVIEW_SCHEMA.json" --private-validated "$O/private/packet_${i}_VALIDATED_PRIVATE.jsonl" --private-errors "$O/private/packet_${i}_ERRORS_PRIVATE.jsonl" --public-receipt "$O/public/packet_${i}_RECEIPT_PUBLIC.json" --expected-records 5 || result=1
done
exit "$result"
