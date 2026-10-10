#!/bin/bash
#SBATCH --job-name=d64-wzrollqa
#SBATCH --partition=wzhdtest
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/rolling/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/rolling/logs/qa-%j.err
set -eo pipefail
umask 077
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u
export PYTHONPATH=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60/code:/work/home/lilysharp/linkup_release_v1/runtime_py38
python3 /work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_engineering_patch_20261010/rolling/code/wz_rolling_qa.py
