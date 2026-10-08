#!/bin/bash -l
#$ -N linkup_q32_final
#$ -cwd
#$ -j y
set -euo pipefail
: "${BU_ROOT:?}"; B=${BU_ROOT}/bundle; I=${BU_ROOT}/imported; R=${BU_ROOT}/run
module load python3/3.8.10
export PYTHONPATH="${R}/python_vendor${PYTHONPATH:+:${PYTHONPATH}}"
mkdir -p "${BU_ROOT}/results" "${BU_ROOT}/return/payload"
python3 "${B}/code/finalize_fixed32_cpu.py" --source "${I}/prepared/SOURCE32_PRIVATE.jsonl" --reference "${I}/prepared/REFERENCE32_FINAL_CANDIDATES_PRIVATE.jsonl" --run-root "${R}/merged" --exporter-dir "${B}/archive/production_standard_20261008" --output "${BU_ROOT}/results/qualification"
cp -a "${BU_ROOT}/results" "${BU_ROOT}/return/payload/"
mkdir -p "${BU_ROOT}/return/payload/tasks"
cp -aL "${R}/merged/tasks/." "${BU_ROOT}/return/payload/tasks/"
python3 - "${BU_ROOT}/return/payload" "${BU_ROOT}/return/RETURN_MANIFEST_PRIVATE.json" <<'PY'
import hashlib,json,pathlib,sys
root,out=map(pathlib.Path,sys.argv[1:]); files=[]
for p in sorted(x for x in root.rglob('*') if x.is_file()):
 b=p.read_bytes(); files.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
out.write_text(json.dumps({'schema_version':'linkup-bu-return-manifest-v1','file_count':len(files),'files':files},indent=2,sort_keys=True)+'\n')
PY
tar -C "${BU_ROOT}/return" -cf "${BU_ROOT}/return/BU_RETURN_PRIVATE.tar" payload RETURN_MANIFEST_PRIVATE.json
python3 - "${BU_ROOT}" <<'PY'
import hashlib,json,os,pathlib,sys,time
root=pathlib.Path(sys.argv[1]); tar=root/'return/BU_RETURN_PRIVATE.tar'; b=tar.read_bytes()
x={'schema_version':'linkup-bu-return-receipt-v1','status':'ready_for_verified_return','job_id':os.environ.get('JOB_ID'),'node':os.uname().nodename,'archive_bytes':len(b),'archive_sha256':hashlib.sha256(b).hexdigest(),'records':32,'delete_authorized':False,'note':'Delete the unique BU root only after this archive and manifest are verified on Kunshan.'}
(root/'return/BU_RETURN_RECEIPT.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
PY
