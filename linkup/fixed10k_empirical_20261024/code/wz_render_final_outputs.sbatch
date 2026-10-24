#!/bin/bash
#SBATCH --job-name=fixed10k_render
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/logs/%x-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/logs/%x-%j.err
set -eo pipefail
source /etc/profile
set -u
module load apps/anaconda3/2023.09
ROOT=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024
test ! -e "$ROOT/public/FINAL_RENDER_RECEIPT_PUBLIC.json" || { echo "guard: final render already complete"; exit 0; }
python "$ROOT/code/render_final_outputs.py" --public "$ROOT/public"
