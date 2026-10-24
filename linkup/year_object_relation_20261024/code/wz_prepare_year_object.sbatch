#!/bin/bash
#SBATCH --job-name=lk-year-input
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/year_object_relation_20261024/logs/input-%j.out
#SBATCH --error=/work/home/lilysharp/private/year_object_relation_20261024/logs/input-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module load apps/anaconda3/2023.09
umask 077
export PYTHONDONTWRITEBYTECODE=1
R=/work/home/lilysharp/private/year_object_relation_20261024
OLD=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
F=/work/home/lilysharp/private/formal800_20261012/code/frozen_rulefirst_v1_2
python "$R/code/prepare_year_object.py" \
  --recovered "$OLD/recovered" --input-manifest "$OLD/INPUT_MANIFEST_PRIVATE.json" \
  --frozen-rule-dir "$F" \
  --expected-rule-sha256 e429463ddfe947587c5d1afaea2aa87ab287bf91144496e09c7819bb53f71526 \
  --expected-legacy-sha256 336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd \
  --analysis-frame /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/empirical_20261024/private/AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet \
  --output "$R/inputs_v1"
cp "$R/inputs_v1/PREPARATION_PUBLIC.json" "$R/public/PREPARATION_PUBLIC.json"
