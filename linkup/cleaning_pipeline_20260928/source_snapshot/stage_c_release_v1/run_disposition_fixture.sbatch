#!/bin/bash
#SBATCH --job-name=disposition-fixture
#SBATCH --partition=kshctest02
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-fixture-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-fixture-%j.err
set -euo pipefail
cd /public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
/public/software/apps/python/3.8.10/bin/python3 test_prepare_release_dispositions.py
