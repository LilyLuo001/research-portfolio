#!/bin/bash
#SBATCH --job-name=d63-wzctl
#SBATCH --partition=wzhdtest
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/rolling/logs/controller-%j.out
#SBATCH --error=/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/rolling/logs/controller-%j.err
set -euo pipefail;source /etc/profile >/dev/null 2>&1||true;module load python/3.8.10;python3 /work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010/rolling/code/wz_rolling_controller.py
