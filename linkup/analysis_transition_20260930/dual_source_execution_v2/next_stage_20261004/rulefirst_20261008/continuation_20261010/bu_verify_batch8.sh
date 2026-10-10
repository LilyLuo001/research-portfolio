#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=02:00:00
#$ -l mem_per_core=4G
#$ -l no_gpu=TRUE
#$ -hold_jid 8004875
#$ -N lk_qa8
set -euo pipefail
umask 077
module load python3/3.8.10
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010
PYTHONPATH=/projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code:${PYTHONPATH:-} python3 "$ROOT/code/verify_wave_outputs.py" --manifest "$ROOT/control/private/BATCH_0002_MANIFEST_PRIVATE.json" --output-root "$ROOT/output" --verifier /projectnb/econdept/qluo/linkup_rulefirst_20261008/full_production_20261009/code/verify_one_shard_outputs.py --public-receipt "$ROOT/public/BATCH_0002_QA_PUBLIC.json"
