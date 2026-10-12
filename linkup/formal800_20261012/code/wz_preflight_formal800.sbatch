#!/bin/bash
#SBATCH --job-name=formal800-preflight
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/preflight-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/preflight-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
ROOT=/work/home/lilysharp/private/formal800_20261012
FRAME=/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet
umask 077
python3 "$ROOT/code/preflight_formal800.py" --frame "$FRAME" --output "$ROOT/public/PREFLIGHT_RECEIPT_PUBLIC.json"
