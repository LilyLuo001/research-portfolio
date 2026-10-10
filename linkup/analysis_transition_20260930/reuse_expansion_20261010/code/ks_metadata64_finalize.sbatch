#!/bin/bash
#SBATCH --job-name=d67-mfin
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/fin-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/fin-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010; META="$ROOT/metadata_69"; OLD=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60
python3 "$ROOT/code/metadata64_pipeline.py" finalize --base-code "$OLD/code/targeted_metadata_join.py" --array-map "$META/work/ARRAY_MAP_PRIVATE.json" --key-dir "$META/private/keys64" --official-codes /public/home/lilysharp/linkup_analysis_execution_oct02/private/official_onet2019_occupations.csv --first5-metadata "$OLD/output_fast/FIRST5_METADATA_FAST_PRIVATE.parquet" --output64 "$META/private/METADATA64_PRIVATE.parquet" --output69 "$META/private/METADATA69_PRIVATE.parquet" --public-receipt "$META/public/METADATA69_RECEIPT_PUBLIC.json"
