#!/bin/bash -l
#$ -N linkup_q32_diag
#$ -cwd
#$ -j y
set -euo pipefail
: "${BU_ROOT:?}"; module load python3/3.8.10
export PYTHONPATH="${BU_ROOT}/run/python_vendor${PYTHONPATH:+:${PYTHONPATH}}"
python3 "${BU_ROOT}/bundle/code/diagnose_bu_export.py" --root "${BU_ROOT}"
tar -C "${BU_ROOT}" -cf "${BU_ROOT}/diagnostic/BU_DIAGNOSTIC_RETURN_PRIVATE.tar" diagnostic/DIAGNOSTIC_PUBLIC.json diagnostic/DIAGNOSTIC_PRIVATE.json $(test -f "${BU_ROOT}/diagnostic/CORRECTED_FIELD_CANDIDATES_PRIVATE.jsonl" && echo diagnostic/CORRECTED_FIELD_CANDIDATES_PRIVATE.jsonl diagnostic/CORRECTED_EXPORT_PUBLIC.json)
sha256sum "${BU_ROOT}/diagnostic/BU_DIAGNOSTIC_RETURN_PRIVATE.tar" > "${BU_ROOT}/diagnostic/BU_DIAGNOSTIC_RETURN_PRIVATE.tar.sha256"
