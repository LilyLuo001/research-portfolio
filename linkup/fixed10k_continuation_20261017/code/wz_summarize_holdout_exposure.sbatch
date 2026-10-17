#!/bin/bash
#SBATCH --job-name=f10k_holdout_meta
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/continuation/logs/%x_%j.err
set +e;set +u;source /etc/profile;module load python/3.8.10;rc=$?;if [ "$rc" -ne 0 ];then exit "$rc";fi
set -eu;umask 077
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017;C="$T/private/continuation";P="$T/private/batch002_004/batch004/final"
python3 "$C/code/summarize_holdout_exposure.py" --holdout "$C/splits/FINAL_EVALUATION_HOLDOUT_PRIVATE.jsonl" --queue "$P/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl" --ledger "$P/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl" --prep-005-014 "$C/CONTINUATION_PREP_RECEIPT.json" --prep-015-069 "$C/CONTINUATION_PREP_015_069_RECEIPT.json" --output "$C/splits/FINAL_EVALUATION_HOLDOUT_EXPOSURE_RECEIPT.json"
