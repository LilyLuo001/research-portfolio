#!/bin/bash
#SBATCH --job-name=lk-year-network
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/year_object_relation_20261024/logs/network-%j.out
#SBATCH --error=/work/home/lilysharp/private/year_object_relation_20261024/logs/network-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
source "$HOME/proxy.sh" >/dev/null 2>&1
umask 077
for origin in https://huggingface.co https://hf-mirror.com; do
  printf '%s ' "$origin"
  curl -4 --fail --location --silent --show-error --connect-timeout 10 --max-time 25 \
    --output /dev/null --write-out 'http=%{http_code} seconds=%{time_total}\n' \
    "$origin/FacebookAI/xlm-roberta-base/resolve/e73636d4f797dec63c3081bb6ed5c7b0bb3f2089/config.json" || true
done
