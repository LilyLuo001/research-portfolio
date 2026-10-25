#!/bin/bash
#SBATCH --job-name=lk-meta-probe
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/public/home/lilysharp/linkup_metadata_research_20261026/logs/probe-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_metadata_research_20261026/logs/probe-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=1
python /public/home/lilysharp/linkup_metadata_research_20261026/code/probe_metadata.py
