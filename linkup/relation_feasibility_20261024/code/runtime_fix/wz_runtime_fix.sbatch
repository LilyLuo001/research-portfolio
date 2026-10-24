#!/bin/bash
#SBATCH --job-name=lk-runtime-fix
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/runtime-fix-%j.out
#SBATCH --error=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/runtime-fix-%j.err
set +e
set +u
source /etc/profile >/dev/null 2>&1
umask 077
export LC_ALL=C LANG=C
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
W=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
OUT="$W/public/RUNTIME_FIX_${SLURM_JOB_ID}_PUBLIC.json"
module purge
for runtime_module in compiler/devtoolset/7.3.1 compiler/dtk/22.10.1 mpi/hpcx/gcc-7.3.1 apps/Pytorch/llama_py38; do
  printf 'loading=%s\n' "$runtime_module"
  module load "$runtime_module"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '{"runtime_qualified":false,"scheduler_job_id":"%s","failed_module":"%s","module_exit":%s}\n' "$SLURM_JOB_ID" "$runtime_module" "$rc" > "$OUT"
    exit "$rc"
  fi
done
module list 2>&1
PY=/public/software/apps/DeepLearning/PyTorch_Lib/llama_py38/bin/python3.8
printf 'interpreter=%s\n' "$PY"
if [ ! -x "$PY" ]; then
  printf '{"runtime_qualified":false,"scheduler_job_id":"%s","failure":"Existing llama_py38 absolute interpreter absent on compute node"}\n' "$SLURM_JOB_ID" > "$OUT"
  exit 3
fi
timeout 180 "$PY" "$W/code/runtime_fix/probe_runtime.py" "$OUT"
rc=$?
if [ ! -e "$OUT" ]; then
  printf '{"runtime_qualified":false,"scheduler_job_id":"%s","failure":"Probe interpreter exited or timed out before JSON","probe_exit":%s}\n' "$SLURM_JOB_ID" "$rc" > "$OUT"
fi
printf 'probe_exit=%s\n' "$rc"
exit "$rc"
