#!/bin/bash
#SBATCH --job-name=linkup-wz-key-stage
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=04:00:00
#SBATCH --output=/public/home/lilysharp/linkup_release_v1/logs/wz-key-stage-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_release_v1/logs/wz-key-stage-%j.err
set -euo pipefail
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
/public/software/apps/python/3.8.10/bin/python3 /public/home/lilysharp/linkup_release_v1/stage_wuzhen_occurrences.py \
  --output /public/home/lilysharp/linkup_release_v1/wz_occurrences_stage \
  --remote-root /public/home/lilysharp/linkup_analysis_v1/stage_b_huazhong/match_v1/incremental/batches \
  --ks-projection-report /public/home/lilysharp/linkup_analysis_v1/stage_b/full_key_audit_v1/projection-job-122987596/projection_report.json \
  --host zzeshell.scnet.cn --port 65032 --user lilysharp \
  --key /public/home/lilysharp/.ssh/hz_transfer_20260928 \
  --known-hosts /public/home/lilysharp/.ssh/hz_known_hosts_20260928 \
  --control-path /tmp/linkup-hz-wzstage-${SLURM_JOB_ID}-%r-%h-%p \
  --stage-cap-bytes 4000000000
