#!/bin/bash
#SBATCH --job-name=d64-semantic12
#SBATCH --partition=wzhdtest
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_semantic_packet/logs/semantic-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_semantic_packet/logs/semantic-%j.err
set -eo pipefail
umask 077
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/linkup_release_v1/runtime_py38
python3 /work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/d64_semantic_packet/code/build_targeted_packet.py
