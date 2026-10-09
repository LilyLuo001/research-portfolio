#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 4
#$ -l h_rt=02:00:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_full4_4
export TASK_INDEX=4
exec bash /projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code/bu_run_next4_array.sh
