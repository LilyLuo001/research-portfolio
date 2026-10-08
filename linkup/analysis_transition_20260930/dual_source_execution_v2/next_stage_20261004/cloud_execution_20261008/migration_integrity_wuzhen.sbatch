#!/bin/bash
#SBATCH --job-name=linkup-cloud-migrate-verify
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00

set -euo pipefail

set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
set -u

run_root=${LINKUP_CLOUD_RUN_ROOT:?LINKUP_CLOUD_RUN_ROOT is required}
payload_root="${run_root}/payload"
manifest="${run_root}/transport_manifest.sha256"
receipt="${run_root}/MIGRATION_INTEGRITY_RECEIPT.json"

umask 077
cd "${payload_root}"

sha256sum -c "${manifest}" > "${run_root}/manifest_check.log"

for required in \
  production_standard_20261008 \
  batch002_execution \
  continuous_production_20261008 \
  compact_measurement_20261007
do
  test -d "${required}"
done

if find . -type f \( \
  -name 'UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' -o \
  -name 'REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' -o \
  -name 'REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl' -o \
  -name 'SOURCE_PRIVATE.jsonl' -o \
  -name 'COMBINED_SOURCE_PRIVATE.jsonl' -o \
  -name 'UNBLIND_PRIVATE.jsonl' \
\) -print -quit | grep -q .; then
  echo "excluded raw/original-text payload detected" >&2
  exit 23
fi

manifest_sha256=$(sha256sum "${manifest}" | awk '{print $1}')
archive_sha256=$(awk '{print $1}' "${run_root}/active_artifacts.tar.gz.sha256")
file_count=$(wc -l < "${manifest}" | tr -d ' ')
payload_bytes=$(du -sb "${payload_root}" | awk '{print $1}')
verified_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "${receipt}" "${SLURM_JOB_ID}" "${SLURM_JOB_PARTITION:-wzhdtest}" \
  "${run_root}" "${manifest_sha256}" "${archive_sha256}" "${file_count}" \
  "${payload_bytes}" "${verified_at}" <<'PY'
import json
import sys

(receipt, job_id, partition, run_root, manifest_sha256, archive_sha256,
 file_count, payload_bytes, verified_at) = sys.argv[1:]

result = {
    "schema_version": "linkup-cloud-migration-integrity-v1",
    "status": "verified",
    "verification_kind": "scheduled-cloud-transport-integrity-only",
    "job_id": job_id,
    "partition": partition,
    "run_root": run_root,
    "manifest_sha256": manifest_sha256,
    "archive_sha256": archive_sha256,
    "file_count": int(file_count),
    "payload_bytes": int(payload_bytes),
    "verified_at_utc": verified_at,
    "required_directories": [
        "production_standard_20261008",
        "batch002_execution",
        "continuous_production_20261008",
        "compact_measurement_20261007",
    ],
    "origin_labels": {
        "historical_labels_and_predictions": "preserved local/Codex artifacts; not cloud inference",
        "cloud_job_output": "transport integrity verification only",
    },
    "inference_performed": False,
    "production_claim": False,
}
with open(receipt, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

cat "${receipt}"
