#!/bin/bash
#SBATCH --job-name=lk-year-tail
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/year_object_relation_20261024/logs/tail-%j.out
#SBATCH --error=/work/home/lilysharp/private/year_object_relation_20261024/logs/tail-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module load apps/anaconda3/2023.09
source "$HOME/proxy.sh" >/dev/null 2>&1
umask 077
export PYTHONDONTWRITEBYTECODE=1
python /work/home/lilysharp/private/year_object_relation_20261024/code/stage_resume_tail.py
