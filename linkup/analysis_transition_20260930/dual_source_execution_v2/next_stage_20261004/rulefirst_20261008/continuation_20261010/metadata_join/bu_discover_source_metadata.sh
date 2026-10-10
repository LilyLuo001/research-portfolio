#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -l no_gpu=TRUE
#$ -pe omp 1
#$ -l h_rt=00:05:00
#$ -l mem_per_core=2G
#$ -N lk_meta_inv
set -euo pipefail
umask 077
module load python3/3.8.10
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010/metadata_join
python3 "$ROOT/code/discover_source_metadata.py" \
  --credential-dir /projectnb/econdept/qluo/.linkup_transfer_credentials_20261010 \
  --private-output "$ROOT/source_metadata_private" \
  --public-receipt "$ROOT/output/SOURCE_METADATA_DISCOVERY_RECEIPT_PUBLIC.json"
