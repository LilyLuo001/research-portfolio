#!/bin/bash
#SBATCH --job-name=formal800-weight-audit
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/weight_lineage_20261012/logs/audit-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/weight_lineage_20261012/logs/audit-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
ROOT=/work/home/lilysharp/private/formal800_20261012/weight_lineage_20261012
FORMAL=/work/home/lilysharp/private/formal800_20261012
FRAME=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet
python3 "$ROOT/code/audit_sample_weight_lineage.py" \
  --frame "$FRAME" \
  --allocation "$ROOT/input/cell_allocation.csv" \
  --hidden-linkage "$FORMAL/private/freeze/HIDDEN_LINKAGE_PRIVATE.jsonl" \
  --freeze-receipt "$ROOT/input/FORMAL800_FREEZE_RECEIPT_PUBLIC.json" \
  --output "$ROOT/public/WEIGHT_LINEAGE_AUDIT_RECEIPT.json"
