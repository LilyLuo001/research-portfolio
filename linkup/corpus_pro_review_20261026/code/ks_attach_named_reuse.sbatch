#!/bin/bash
#SBATCH --job-name=lk-pro-exact-reuse
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/reuse-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/reuse-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_corpus_pro_review_20261026/runtime_existing/runtime_jsonschema:/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
B=${REVIEW_BATCH:?}
IFS=: read -r -a references <<< "${REFERENCE_CHECKPOINTS:?}"
python "$R/code/attach_exact_reuse.py" --batch-dir "$R/$B" --reference-checkpoints "${references[@]}" --output-root "$R/reuse_bindings/$B/$SLURM_JOB_ID"
