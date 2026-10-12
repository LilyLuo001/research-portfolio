#!/bin/bash
#SBATCH --job-name=formal800-exclhash
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=/public/home/lilysharp/formal800_20261012/public/exclhash-%j.out
#SBATCH --error=/public/home/lilysharp/formal800_20261012/public/exclhash-%j.err
set -eo pipefail
set +u
source /etc/profile.d/modules.sh
module load python/3.8.10
set -u
ROOT=/public/home/lilysharp/formal800_20261012
BASE=/public/home/lilysharp/linkup_rulefirst_20261008
mkdir -p "$ROOT/private/exclusions" "$ROOT/public"; chmod 700 "$ROOT" "$ROOT/private" "$ROOT/private/exclusions" "$ROOT/public"; umask 077
python3 "$ROOT/code/build_exclusion_hashes.py" \
 --input "$BASE/imported/batch002_execution/private/batch002/COMBINED_SOURCE_PRIVATE.jsonl" \
 --input "$BASE/imported/batch002_execution/private/batch002/UNBLIND_MANIFEST_PRIVATE.jsonl" \
 --input "$BASE/imported/batch002_execution/private/cumulative_checkpoint/COMPLETED_SOURCE_HASH_LEDGER_PRIVATE.jsonl" \
 --input "$BASE/imported/compact_measurement_20261007/private/source20_pack/UNBLIND_MANIFEST_PRIVATE.jsonl" \
 --input "$BASE/imported/continuous_production_20261008/private/batch003/UNBLIND_PRIVATE.jsonl" \
 --input "$BASE/imported/continuous_production_20261008/private/batch004/UNBLIND_PRIVATE.jsonl" \
 --input "$BASE/imported/production_standard_20261008/private/batch001/UNBLIND_MANIFEST_PRIVATE.jsonl" \
 --input "$BASE/run/prep/DEV120_SOURCE_PRIVATE.jsonl" --input "$BASE/run/eval80/RULE_OUTPUTS_PRIVATE.jsonl" \
 --input "$BASE/pro_review_wave02_20261012/private/selection/WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl" \
 --output "$ROOT/private/exclusions/EXCLUSION_HASHES_ONLY_PRIVATE.jsonl" --receipt "$ROOT/public/EXCLUSION_HASHES_RECEIPT_PUBLIC.json"
