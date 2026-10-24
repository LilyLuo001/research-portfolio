#!/bin/bash
#SBATCH --job-name=lk-design-corr
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:30:00
#SBATCH --output=/work/home/lilysharp/private/design_correction_20261024/logs/correction-%j.out
#SBATCH --error=/work/home/lilysharp/private/design_correction_20261024/logs/correction-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=/work/home/lilysharp/private/design_correction_20261024
H="$R/handoff_private"
test ! -e "$R/run001/public/RUN_RECEIPT_PUBLIC.json" || { echo completed_correction_guard; exit 0; }
test -e "$H/HANDOFF_PUBLIC.json"
cd "$R/inputs/parent16"
sha256sum -c PARENT_SOURCE_SHA256SUMS.txt
cd "$R/code"
python test_correction_core.py
args=()
for p in "$R"/inputs/parent16/[0-9a-f].parquet; do args+=(--parent "$p"); done
python run_design_correction.py "${args[@]}" \
  --fixed "$H/FIXED_KEYS_WEIGHTS_PRIVATE.parquet" \
  --reference "$H/REFERENCE_AD_LEVEL_PRIVATE.parquet" \
  --reference-receipt "$H/EMPIRICAL_RECEIPT_PUBLIC.json" \
  --isolation-register "$H/ISOLATION_PRIVATE.jsonl" \
  --allocation "$H/cell_allocation.csv" \
  --private-output "$R/run001/private" --public-output "$R/run001/public" \
  --threads 8 --memory-limit 12GB --enable-design-se
