#!/bin/bash
#SBATCH --job-name=fx10k-final-fit
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/final-fit-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/logs/final-fit-%j.err
set -eo pipefail
set +u
source /etc/profile
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
C="$T/private/continuation"
B="$T/private/baseline_optimized"
F=/work/home/lilysharp/private/formal800_20261012
OUT="$B/final_fit"
mkdir -p "$OUT"
python "$B/code/final_fit.py" freeze \
  --ledger "$C/prepared/batch069/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" \
  --queue "$C/prepared/batch069/final/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" \
  --receipt "$C/receipts/BATCH069_FINALIZE_RECEIPT.json" \
  --holdout "$C/splits/FINAL_EVALUATION_HOLDOUT_PRIVATE.jsonl" \
  --frame /work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet \
  --normalizer "$F/code/frozen_rulefirst_v1_2/legacy_v5_frozen.py" \
  --legacy "$T/private/baseline/code/train_evaluate_infer.py" \
  --isolation "$C/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl" \
  --output "$OUT/FINAL_INPUT_FREEZE_PRIVATE.json"
python "$B/code/final_fit.py" fit \
  --freeze "$OUT/FINAL_INPUT_FREEZE_PRIVATE.json" --output "$OUT/run"
