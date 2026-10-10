#!/bin/bash
#SBATCH --job-name=d61-meta-join
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/public/join-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/public/join-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 /public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/code/ks_run_first5_metadata.py
