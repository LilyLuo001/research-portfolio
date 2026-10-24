#!/bin/bash
#SBATCH --job-name=lk-rel-runtime
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/runtime-%j.out
#SBATCH --error=/work/home/lilysharp/private/linkup_relation_feasibility_20261024/logs/runtime-%j.err
set +e
set +u
set -o pipefail
source /etc/profile >/dev/null 2>&1
profile_rc=$?
printf 'profile_rc=%s\n' "$profile_rc"
module purge
printf 'module_purge_rc=%s\n' "$?"
umask 077
export LC_ALL=C LANG=C
W=/work/home/lilysharp/private/linkup_relation_feasibility_20261024
# Preserve successful supervision recovery and the original failed probe logs.
if [ -e "$W/public/INSTALLED_RUNTIME_PUBLIC.json" ]; then
  echo 'Existing probe result preserved; refusing repeat.' >&2
  exit 2
fi
mkdir -p "$W/RUNTIME_REPAIR_STARTED"
for runtime_module in compiler/devtoolset/7.3.1 compiler/dtk/22.04.1 mpi/hpcx/gcc-7.3.1 apps/Pytorch/1.10.0; do
  printf 'loading=%s\n' "$runtime_module"
  module load "$runtime_module"
  module_rc=$?
  if [ "$module_rc" -ne 0 ]; then
    printf '{"module_load_succeeded":false,"failed_module":"%s","exit_code":%s}\n' "$runtime_module" "$module_rc" > "$W/public/INSTALLED_RUNTIME_PUBLIC.json"
    exit 0
  fi
done
set -eu
command -v python3
python3 --version
python3 "$W/code/runtime_probe.py" "$W/public/INSTALLED_RUNTIME_PUBLIC.json"
