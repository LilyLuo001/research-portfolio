#!/bin/bash -l
#$ -P econdept
#$ -N p1net20
#$ -l h_rt=00:20:00
#$ -l mem_per_core=4G
#$ -pe omp 2
#$ -j n

set -euo pipefail
module load python3/3.12.4

stage_dir=/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920_phase3/network_selection
data_root=/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared

cd "$stage_dir"
python build_weighted_receiver_selection.py \
  --root "$data_root" \
  --out "$stage_dir/results"
