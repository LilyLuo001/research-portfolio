#!/bin/bash -l
# Submit only after Kunshan verification writes RETURN_VERIFIED_KUNSHAN.json into BU_ROOT.
#$ -N linkup_q32_delete
#$ -cwd
#$ -j y
set -euo pipefail
: "${BU_ROOT:?}"; test "${BU_ROOT}" = /projectnb/econdept/qluo/linkup_cpu_qualification_20261008_bu
OUT=/projectnb/econdept/qluo/linkup_cpu_qualification_20261008_bu_DELETION_RECEIPT.json
python3 - "${BU_ROOT}" <<'PY'
import hashlib,json,pathlib,sys
r=pathlib.Path(sys.argv[1]); receipt=json.loads((r/'return/BU_RETURN_RECEIPT.json').read_text()); verified=json.loads((r/'RETURN_VERIFIED_KUNSHAN.json').read_text())
if verified.get('archive_sha256')!=receipt.get('archive_sha256') or verified.get('status')!='verified_on_kunshan': raise SystemExit('return verification mismatch')
PY
find "${BU_ROOT}" -mindepth 1 -delete
rmdir "${BU_ROOT}"
printf '{"schema_version":"linkup-bu-deletion-v1","status":"deleted_after_verified_kunshan_return","deleted_root":"%s","job_id":"%s"}\n' "${BU_ROOT}" "${JOB_ID}" > "${OUT}"
