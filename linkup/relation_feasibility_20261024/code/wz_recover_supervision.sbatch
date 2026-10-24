#!/bin/bash
#SBATCH --job-name=lk-rel-supervision
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/recover-%j.out
#SBATCH --error=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/recover-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1
module load apps/anaconda3/2023.09
set -u
umask 077
unset PYTHONPATH
export LC_ALL=C LANG=C
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
W=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private
F=/work/home/lilysharp/private/formal800_20261012
# Atomic create-only guard: preserve a failed attempt instead of overwriting it.
mkdir "$W/RECOVER_STARTED"
python "$W/code/prepare_manifest.py" --private-root "$T" \
  --formal-reviews "$F/private/validation/final/validated_reviews.jsonl" \
  --freeze "$T/baseline_optimized/final_fit/FINAL_INPUT_FREEZE_PRIVATE.json" \
  --output "$W/INPUT_MANIFEST_PRIVATE.json"
python "$W/code/materialize_supervision.py" --manifest "$W/INPUT_MANIFEST_PRIVATE.json" --output "$W/recovered"
cp "$W/recovered/RECOVERABILITY_PUBLIC.json" "$W/public/RECOVERABILITY_PUBLIC.json"
# Probe exactly one preinstalled PyTorch module after supervision recovery.
set +u
module purge
if module load compiler/dtk/22.04.1 mpi/hpcx/gcc-7.3.1 compiler/devtoolset/7.3.1 apps/Pytorch/1.10.0; then
  set -u
  python "$W/code/runtime_probe.py" "$W/public/INSTALLED_RUNTIME_PUBLIC.json"
else
  printf '{"module":"apps/Pytorch/1.10.0","module_load_succeeded":false}\n' > "$W/public/INSTALLED_RUNTIME_PUBLIC.json"
fi
