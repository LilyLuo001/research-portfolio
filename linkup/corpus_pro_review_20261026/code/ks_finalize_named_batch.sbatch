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
B=${REVIEW_BATCH:?named prepared batch required}
E="$R/reviews_private"
shopt -s nullglob
patches=("$R/reviews_private/${B}_packet_"*"_PRIMARY_correction.jsonl")
if [[ ${#patches[@]} -gt 0 ]]; then
  E="$R/reviews_effective_${B}_${SLURM_JOB_ID}_private"
  patch_args=(--batch-dir "$R/$B" --reviews-dir "$R/reviews_private" --patches "${patches[@]}" --output-dir "$E")
  if [[ -n "${PRIOR_REVIEWS_DIR:-}" ]]; then patch_args+=(--prior-checkpoint "${PRIOR_CHECKPOINT:?}" --prior-effective-reviews-dir "$PRIOR_REVIEWS_DIR"); fi
  python "$R/code/apply_declared_patches.py" "${patch_args[@]}"
fi
args=(--batch-dir "$R/$B" --reviews-dir "$E" --output-root "$R/checkpoints/$SLURM_JOB_ID" --dispatcher-file "$R/code/DISPATCHER_${B}_PUBLIC.json")
if [[ -n "${PRIOR_CHECKPOINT:-}" ]]; then args+=(--prior-checkpoint "$PRIOR_CHECKPOINT"); fi
python "$R/code/checkpoint_reviews.py" "${args[@]}"
