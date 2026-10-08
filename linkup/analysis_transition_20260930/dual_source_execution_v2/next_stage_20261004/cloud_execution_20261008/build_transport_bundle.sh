#!/bin/bash
set -euo pipefail

stage_root=$(cd "$(dirname "$0")/.." && pwd)
audit_root="${stage_root}/cloud_execution_20261008"
bundle_root="${audit_root}/transport"
file_list="${bundle_root}/transport_files.nul"
manifest="${bundle_root}/transport_manifest.sha256"
archive="${bundle_root}/active_artifacts.tar.gz"

mkdir -p "${bundle_root}"

cd "${stage_root}"
find \
  production_standard_20261008 \
  batch002_execution \
  continuous_production_20261008 \
  compact_measurement_20261007 \
  -type f \
  ! -path '*/__pycache__/*' \
  ! -path '*/.pytest_cache/*' \
  ! -name '.DS_Store' \
  ! -name 'UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' \
  ! -name 'REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' \
  ! -name 'REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl' \
  ! -name 'SOURCE_PRIVATE.jsonl' \
  ! -name 'COMBINED_SOURCE_PRIVATE.jsonl' \
  ! -name 'UNBLIND_PRIVATE.jsonl' \
  -print0 | sort -z > "${file_list}"

: > "${manifest}"
while IFS= read -r -d '' relative_path; do
  digest=$(shasum -a 256 "${relative_path}" | awk '{print $1}')
  printf '%s  %s\n' "${digest}" "${relative_path}" >> "${manifest}"
done < "${file_list}"

COPYFILE_DISABLE=1 tar -czf "${archive}" --null -T "${file_list}"
shasum -a 256 "${archive}" > "${bundle_root}/active_artifacts.tar.gz.sha256"
wc -c "${archive}" "${manifest}" > "${bundle_root}/transport_sizes.txt"
