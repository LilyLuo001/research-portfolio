#!/bin/bash
#SBATCH --job-name=d67-mprep
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/prep-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/metadata_69/public/prep-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010; META="$ROOT/metadata_69"; OLD=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60
python3 "$ROOT/code/build_metadata64_inputs.py" --frozen "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" --wz-dir "$META/private/input_keys_wz" --ks-dir "$META/private/input_keys_ks" --output "$META/private/METADATA64_INPUTS_PRIVATE.json"
python3 "$ROOT/code/metadata64_pipeline.py" prepare-keys --base-code "$OLD/code/targeted_metadata_join.py" --inputs-manifest "$META/private/METADATA64_INPUTS_PRIVATE.json" --key-dir "$META/private/keys64" --public-receipt "$META/public/KEYS64_RECEIPT_PUBLIC.json"
python3 "$ROOT/code/metadata64_pipeline.py" prepare-specs --root "$META" --key-dir "$META/private/keys64" --key-receipt "$META/public/KEYS64_RECEIPT_PUBLIC.json" --records-inventory "$OLD/work/RECORDS_INVENTORY_PRIVATE.json" --onet-inventory "$OLD/work/ONET_INVENTORY_PRIVATE.json" --array-map "$META/work/ARRAY_MAP_PRIVATE.json"
