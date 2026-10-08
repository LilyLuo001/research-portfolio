#!/bin/bash
set -euo pipefail

stage_root=$(cd "$(dirname "$0")/.." && pwd)
bundle_root="${stage_root}/cloud_execution_20261008/transport"
file_list="${bundle_root}/supplement_files.nul"
manifest="${bundle_root}/supplement_manifest.sha256"
archive="${bundle_root}/active_source_supplement.tar.gz"

mkdir -p "${bundle_root}"
cd "${stage_root}"

find \
  production_standard_20261008 \
  batch002_execution \
  continuous_production_20261008 \
  compact_measurement_20261007 \
  -type f \( \
    -name 'UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' -o \
    -name 'REMAINING_UNIQUE_EXACT_TEXT_QUEUE_PRIVATE.jsonl' -o \
    -name 'REPRESENTED_FIXED10000_KEYS_PRIVATE.jsonl' -o \
    -name 'SOURCE_PRIVATE.jsonl' -o \
    -name 'COMBINED_SOURCE_PRIVATE.jsonl' -o \
    -name 'UNBLIND_PRIVATE.jsonl' \
  \) -print0 | sort -z > "${file_list}"

: > "${manifest}"
while IFS= read -r -d '' relative_path; do
  digest=$(shasum -a 256 "${relative_path}" | awk '{print $1}')
  printf '%s  %s\n' "${digest}" "${relative_path}" >> "${manifest}"
done < "${file_list}"

COPYFILE_DISABLE=1 tar -czf "${archive}" --null -T "${file_list}"
shasum -a 256 "${archive}" > "${bundle_root}/active_source_supplement.tar.gz.sha256"
cat "${bundle_root}/transport_manifest.sha256" "${manifest}" \
  | LC_ALL=C sort -k2,2 > "${bundle_root}/combined_manifest.sha256"
wc -c "${archive}" "${manifest}" "${bundle_root}/combined_manifest.sha256" \
  > "${bundle_root}/supplement_sizes.txt"
