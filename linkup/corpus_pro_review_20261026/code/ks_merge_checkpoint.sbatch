#!/bin/bash
#SBATCH --job-name=lk-pro-merge
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/merge-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/merge-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
: "${BATCH001_CHECKPOINT:?required}"
: "${BATCH002_CHECKPOINT:?required}"
: "${BATCH003_CHECKPOINT:?required}"
: "${AUDIT_OVERLAY:?required}"
python "$R/code/merge_checkpoints.py" \
  --checkpoints "$BATCH001_CHECKPOINT" "$BATCH002_CHECKPOINT" "$BATCH003_CHECKPOINT" \
  --source-reviews-dir "$R/reviews_private" \
  --audit-dir "$R/reviews_private" \
  --mechanical-provenance "$R/reviews_effective_20261026_private/PATCH_PROVENANCE_PRIVATE.json" \
  --audit-overlay "$AUDIT_OVERLAY" \
  --output-root "$R/merged_checkpoints/$SLURM_JOB_ID"
