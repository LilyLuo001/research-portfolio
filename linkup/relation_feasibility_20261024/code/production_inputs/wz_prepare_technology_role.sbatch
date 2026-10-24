#!/bin/bash
#SBATCH --job-name=lk-tech-inputs
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/tech-input-%j.out
#SBATCH --error=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/tech-input-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1
W=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
F=/work/home/lilysharp/private/formal800_20261012/code/frozen_rulefirst_v1_2
python "$W/code/production_inputs/prepare_technology_role.py" \
  --recovered "$W/recovered" --input-manifest "$W/INPUT_MANIFEST_PRIVATE.json" \
  --frozen-rule-dir "$F" \
  --expected-rule-sha256 e429463ddfe947587c5d1afaea2aa87ab287bf91144496e09c7819bb53f71526 \
  --expected-legacy-sha256 336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd \
  --output "$W/production_inputs_v1"
cp "$W/production_inputs_v1/PREPARATION_PUBLIC.json" "$W/public/TECHNOLOGY_INPUT_PREPARATION_PUBLIC.json"
