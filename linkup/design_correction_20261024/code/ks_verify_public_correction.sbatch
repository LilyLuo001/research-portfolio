#!/bin/bash
#SBATCH --job-name=lk-corr-qa
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_design_correction_20261024/logs/qa-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_design_correction_20261024/logs/qa-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python /public/home/lilysharp/linkup_design_correction_20261024/code/verify_public_correction.py --public-output /public/home/lilysharp/linkup_design_correction_20261024/run001/public
