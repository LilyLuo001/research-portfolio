#!/bin/bash
#SBATCH --job-name=lk-year-fit
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --output=/work/home/lilysharp/private/year_object_relation_20261024/logs/fit-%j.out
#SBATCH --error=/work/home/lilysharp/private/year_object_relation_20261024/logs/fit-%j.err
set -eo pipefail
source /etc/profile >/dev/null 2>&1 || true
module load compiler/devtoolset/7.3.1
module load compiler/dtk/22.10.1
module load mpi/hpcx/gcc-7.3.1
module load apps/Pytorch/llama_py38
umask 077
unset PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
R=/work/home/lilysharp/private/year_object_relation_20261024
/public/software/apps/DeepLearning/PyTorch_Lib/llama_py38/bin/python3.8 \
  "$R/code/fit_year_object.py" --inputs "$R/inputs_v1" \
  --model-dir "$R/models/xlm-roberta-base" \
  --model-manifest "$R/models/MODEL_MANIFEST_PRIVATE.json" --output "$R/fit001"
