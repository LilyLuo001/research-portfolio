#!/bin/bash
#SBATCH --job-name=remote_month_audit
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/remote-month-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_v2/logs/remote-month-%j.err
set -euo pipefail
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
python3 /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/remote_monthly_audit.py --source '/public/home/lilysharp/dewey_downloads/data/dewey_remote_table/remote-tag/*.parquet' --out /public/home/lilysharp/linkup_analysis_v1/stage_c_v2/remote_monthly_audit_v1 --threads 8
