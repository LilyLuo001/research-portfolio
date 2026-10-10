#!/bin/bash -l
#SBATCH --job-name=lk_bu13qa
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/returned_BU13_d60/public/verify.%j.log
set -euo pipefail
umask 077
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/returned_BU13_d60
source /etc/profile
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38:$ROOT/code${PYTHONPATH:+:$PYTHONPATH}
python3 "$ROOT/code/verify_return_manifest.py" --root "$ROOT" --manifest "$ROOT/control/RETURN_MANIFEST_PRIVATE.json" --output "$ROOT/public/TRANSPORT_VERIFICATION_PUBLIC.json"
python3 "$ROOT/code/verify_shard_set_outputs.py" --manifest "$ROOT/control/BU13_SET_MANIFEST_PRIVATE.json" --verifier "$ROOT/code/verify_one_shard_outputs.py" --allowed-root "$ROOT" --output "$ROOT/public/SHARD_SET_13_QA_PUBLIC.json"
python3 - <<'PY'
import datetime,hashlib,json,os,platform,pyarrow
root='/public/home/lilysharp/linkup_rulefirst_20261008/returned_BU13_d60'
def sha(p):return hashlib.sha256(open(p,'rb').read()).hexdigest()
x={'status':'complete','version':'d60-bu13-domestic-verification-v1','job_id':os.environ.get('SLURM_JOB_ID'),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':{'python':platform.python_version(),'pyarrow':pyarrow.__version__},'transport_verification_sha256':sha(root+'/public/TRANSPORT_VERIFICATION_PUBLIC.json'),'set_qa_sha256':sha(root+'/public/SHARD_SET_13_QA_PUBLIC.json'),'api_calls':0,'model_calls':0,'semantic_rerun':False}
p=root+'/public/BU13_DOMESTIC_RUN_RECEIPT_PUBLIC.json';open(p,'w').write(json.dumps(x,indent=2,sort_keys=True)+'\n')
PY
rm -f "$ROOT/control/TRANSPORT_COMPLETE_UNVERIFIED"
: > "$ROOT/control/TRANSPORT_AND_QA_COMPLETE"
