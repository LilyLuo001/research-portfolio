#!/bin/bash
#SBATCH --job-name=d61-fast-x
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --array=1-4%4
#SBATCH --output=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/public/fast-x-%A_%a.out
#SBATCH --error=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60/public/fast-x-%A_%a.err
set -euo pipefail
source /etc/profile.d/modules.sh
module load python/3.8.10
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ROOT=/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60
cd "$ROOT"
SPEC=$(python3 - "$SLURM_ARRAY_TASK_ID" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path('/public/home/lilysharp/linkup_rulefirst_20261008/continuation_20261010/metadata_join_first5_d60');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=json.load(open(r/'public/FAST_EXTRACT_QUALIFICATION_PUBLIC.json'));m=json.load(open(r/'work_fast/FAST_ARRAY_MAP_PRIVATE.json'))
assert sha(r/'public/FAST_EXTRACT_QUALIFICATION_PUBLIC.json')=='eb94ab0866c8a9d9bb1c7365bd41c1e1d5c6098285b53392d0a86999158a1350'
assert m['qualification_receipt_sha256']=='eb94ab0866c8a9d9bb1c7365bd41c1e1d5c6098285b53392d0a86999158a1350' and m['base_code_sha256']=='d44ee0be0f8f3c7b93fd5d5ff72aa375d92a257c0481ab7978b29637cbd2ded2' and m['fast_code_sha256']=='598615d8d93c3c14cfbab8869508949ebeab61fcae5adc91281acad4a37dd161'
assert q['status']=='pass' and q['base_code_sha256']=='d44ee0be0f8f3c7b93fd5d5ff72aa375d92a257c0481ab7978b29637cbd2ded2' and q['fast_code_sha256']=='598615d8d93c3c14cfbab8869508949ebeab61fcae5adc91281acad4a37dd161'
assert sha(r/'code/targeted_metadata_join.py')==q['base_code_sha256'] and sha(r/'code/fast_extract_batch.py')==q['fast_code_sha256']
e=next(x for x in m['entries'] if x['array_index']==int(sys.argv[1]));assert sha(e['spec'])==e['spec_sha256'];print(e['spec'])
PY
)
python3 "$ROOT/code/fast_extract_batch.py" --batch-spec "$SPEC"
