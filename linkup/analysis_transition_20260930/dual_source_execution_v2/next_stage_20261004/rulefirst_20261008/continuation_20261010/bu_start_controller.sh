#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -hold_jid 8004985
#$ -N lk_ctl
set -euo pipefail
umask 077
module load python3/3.8.10
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010
python3 "$ROOT/code/rolling_controller.py" --root "$ROOT" --master "$ROOT/control/private/regional_runner_plan.jsonl" --ledger "$ROOT/control/private/ROLLING_LEDGER_PRIVATE.json" --wave-size 8
