#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=08:00:00
#$ -l mem_per_core=4G
#$ -l no_gpu=TRUE
#$ -N lk_st8_1
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010
module load python3/3.8.10
python3 "$ROOT/code/stage_manifest.py" --manifest "$ROOT/control/private/BATCH_0002_LANE1_PRIVATE.json" --stage-root "$ROOT/staging" --credential-dir /projectnb/econdept/qluo/.linkup_transfer_credentials_20261010 --cap-bytes 10000000000 --public-receipt "$ROOT/public/BATCH_0002_LANE1_STAGING_RECEIPT_PUBLIC.json"
