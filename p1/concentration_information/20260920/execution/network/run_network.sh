#!/bin/bash -l
#$ -N p1_network_meta
#$ -cwd
#$ -l h_rt=00:15:00
#$ -l mem_per_core=4G
#$ -pe omp 2
set -euo pipefail
module load python3/3.12.4
task_root=/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared
task_out="$task_root/derived/p1_concentration_information/20260920/network"
python3 "$task_out/build_network_support.py" --root "$task_root" --out "$task_out/results" "$@"
