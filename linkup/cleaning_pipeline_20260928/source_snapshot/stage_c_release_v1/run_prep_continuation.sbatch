#!/bin/bash
#SBATCH --job-name=linkup-prep-controller-v2
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=3-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/prep-controller-v2-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/prep-controller-v2-%j.err
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
/public/software/apps/python/3.8.10/bin/python3 "${ROOT}/prep_server_continuation.py"
