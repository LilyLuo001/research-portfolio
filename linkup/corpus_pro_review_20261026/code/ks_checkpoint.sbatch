#!/bin/bash
#SBATCH --job-name=lk-pro-checkpoint
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
dispatcher="$R/code/DISPATCHER_PUBLIC.json"
if [[ "${REVIEW_BATCH:-batch001}" != "batch001" ]]; then
  dispatcher="$R/code/DISPATCHER_${REVIEW_BATCH}_PUBLIC.json"
fi
args=(
  --batch-dir "$R/${REVIEW_BATCH:-batch001}"
  --reviews-dir "${CHECKPOINT_REVIEWS_DIR:-$R/reviews_private}"
  --output-root "$R/checkpoints/$SLURM_JOB_ID"
  --dispatcher-file "$dispatcher"

)
if [[ "${REVIEW_BATCH:-batch001}" == "batch001" ]]; then
  args+=(--legacy-manifest-sha-file "$R/code/DISPATCHER_PUBLIC.json")
fi
if [[ -n "${PRIOR_CHECKPOINT:-}" ]]; then
  args+=(--prior-checkpoint "$PRIOR_CHECKPOINT")
fi
python "$R/code/checkpoint_reviews.py" "${args[@]}"
