#!/bin/bash
#SBATCH --job-name=lk-pro-audit-adjudicate
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/audit-adjudication-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_corpus_pro_review_20261026/logs/audit-adjudication-%j.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/public/home/lilysharp/linkup_corpus_pro_review_20261026
python "$R/private_authoring/create_audit_adjudication.py" \
  --root "$R" \
  --output-root "$R/audit_adjudications_private/$SLURM_JOB_ID"
