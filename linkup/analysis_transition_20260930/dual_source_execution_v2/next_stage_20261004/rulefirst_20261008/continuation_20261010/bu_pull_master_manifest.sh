#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_inv
set -euo pipefail
umask 077
ROOT=/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010
CREDS=/projectnb/econdept/qluo/.linkup_transfer_credentials_20261010
OUT="$ROOT/control/private/regional_runner_plan.jsonl"
TMP="$OUT.partial.${JOB_ID}"
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$CREDS/known_hosts" -o IdentitiesOnly=yes -o ConnectTimeout=15 -i "$CREDS/source_ks_id" -p 65023 lilysharp@cancon.hpccube.com 'cat /public/home/lilysharp/linkup_release_v1/disposition_prep_v1/regional_runner_plan.jsonl' > "$TMP"
test -s "$TMP"
mv "$TMP" "$OUT"
chmod 600 "$OUT"
sha256sum "$OUT" > "$ROOT/control/private/regional_runner_plan.sha256"
wc -l -c "$OUT"
