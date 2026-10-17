#!/bin/bash
#SBATCH --job-name=fx10k-base-public
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/public-%j.out
#SBATCH --error=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/logs/public-%j.err
set -eo pipefail
set +u
source /etc/profile
module load python/3.8.10
set -u
umask 077
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38${PYTHONPATH:+:$PYTHONPATH}
python /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/code/render_public_baseline.py
