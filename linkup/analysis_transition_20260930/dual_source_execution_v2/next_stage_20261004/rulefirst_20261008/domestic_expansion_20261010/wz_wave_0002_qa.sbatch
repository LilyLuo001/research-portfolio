#!/bin/bash
#SBATCH --job-name=d63-wz16qa
#SBATCH --partition=wzhdtest
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002/logs/qa-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002/logs/qa-%j.err
set -euo pipefail;umask 077
OLD=/work/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/domestic_wz_d60;RUNTIME=/work/home/lilysharp/linkup_release_v1/runtime_py38
set +u;source /etc/profile >/dev/null 2>&1||true;module purge >/dev/null 2>&1||true;module load python/3.8.10;set -u;export PYTHONPATH="$OLD/code:$RUNTIME"
python3 /work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/wz_wave_0002/code/qa_wz_wave_0002.py
