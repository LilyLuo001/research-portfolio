#!/bin/bash
#SBATCH --job-name=lk-pro-reuse5
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
python "$R/code/attach_exact_reuse.py" --batch-dir "$R/batch005" --reference-checkpoints "$R/merged_checkpoints/125703514" "$R/checkpoints/125707992" --output-root "$R/reuse_bindings/batch005/$SLURM_JOB_ID"
