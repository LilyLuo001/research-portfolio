#!/bin/bash
#SBATCH --job-name=d67-preagg
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/preagg-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010/public/preagg-%j.err
set -eo pipefail
source /etc/profile.d/modules.sh
set +u
module load python/3.8.10
set -u
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/reuse_expansion_20261010
python3 "$ROOT/code/preaggregate_overlay.py" --manifest "$ROOT/private_input/D67_FROZEN_69_PRIVATE.json" \
 --wz-dir "$ROOT/private/additive_wz" --ks-dir "$ROOT/private/additive_ks" \
 --private-output "$ROOT/private/preaggregate" --public-output "$ROOT/public/preaggregate"
