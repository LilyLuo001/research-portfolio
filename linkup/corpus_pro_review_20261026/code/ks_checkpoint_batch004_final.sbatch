#!/bin/bash
#SBATCH --job-name=lk-pro-batch4
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
E="$R/reviews_effective_batch004_${SLURM_JOB_ID}_private"
python "$R/code/apply_declared_patches.py" --batch-dir "$R/batch004" --reviews-dir "$R/reviews_private" --patches "$R/reviews_private/batch004_packet_0005_0006_PRIMARY_correction.jsonl" "$R/reviews_private/batch004_packet_0010_PRIMARY_correction.jsonl" "$R/reviews_private/batch004_packet_0026_PRIMARY_correction.jsonl" --output-dir "$E"
python "$R/code/checkpoint_reviews.py" --batch-dir "$R/batch004" --reviews-dir "$E" --output-root "$R/checkpoints/$SLURM_JOB_ID" --dispatcher-file "$R/code/DISPATCHER_batch004_PUBLIC.json" --prior-checkpoint "$R/checkpoints/125705698"
