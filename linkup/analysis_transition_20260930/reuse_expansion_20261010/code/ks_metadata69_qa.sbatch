#!/bin/bash
#SBATCH --job-name=d67-mqa
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/qa-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/qa-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010; META="$ROOT/metadata_69"; OLD=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60
python3 "$ROOT/code/qa_metadata69.py" --metadata "$META/private/METADATA69_PRIVATE.parquet" --receipt "$META/public/METADATA69_RECEIPT_PUBLIC.json" --base-code "$OLD/code/targeted_metadata_join.py" --first5-key-dir "$OLD/private/keys" --key64-dir "$META/private/keys64" --work "$META/private/qa_key_partitions" --output "$META/public/METADATA69_QA_PUBLIC.json"
