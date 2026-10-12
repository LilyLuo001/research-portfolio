#!/bin/bash
#SBATCH --job-name=formal800_relation_qa
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/validate-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/validate-%j.err
set -eo pipefail

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077

python3 /work/home/lilysharp/private/formal800_20261012/code/qa_shared_conditions.py > /work/home/lilysharp/private/formal800_20261012/public/SHARED_CONDITION_QA.json
python3 /work/home/lilysharp/private/formal800_20261012/code/run_review_validation.py "$@"
