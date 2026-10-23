#!/bin/bash
#SBATCH --job-name=fx10k-final-adj
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/final-adjudication-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/final-adjudication-%j.err
set -eo pipefail
set +u
source /etc/profile
module load apps/anaconda3/2023.09
set -u
umask 022
unset PYTHONPATH
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

B=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized
python "$B/code/adjudicate_final_fields.py" \
  --evaluation "$B/final_fit/run/FINAL_EVALUATION_PRIVATE.json" \
  --rules "$B/code/FINAL_FIELD_ADOPTION_RULES.json" \
  --output-dir "$B/final_fit/adjudication"
