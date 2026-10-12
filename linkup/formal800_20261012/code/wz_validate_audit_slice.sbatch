#!/bin/bash
#SBATCH --job-name=formal800_auditqa
#SBATCH --partition=wzhdtest
#SBATCH --gres=dcu:Hygon:1
#SBATCH --gres-flags=disable-binding
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/work/home/lilysharp/private/formal800_20261012/public/auditqa-%j.out
#SBATCH --error=/work/home/lilysharp/private/formal800_20261012/public/auditqa-%j.err
set -eo pipefail
set +u
source /etc/profile >/dev/null 2>&1 || true
module load python/3.8.10
export PYTHONPATH=/work/home/lilysharp/private/formal800_20261012/runtime_jsonschema:/work/home/lilysharp/linkup_release_v1/runtime_py38
set -u
umask 077
# These consecutive file slices are transport/reading units of the frozen audit;
# they do not select any new advertisements or change the fixed audit sample.
python3 - "$1" "${2:-r1}" <<'PY'
import json, subprocess, sys
from pathlib import Path
w=Path('/work/home/lilysharp/private/formal800_20261012')
n=int(sys.argv[1]); revision=sys.argv[2]
if n not in range(1,9) or not revision.isalnum():
    raise RuntimeError('expected audit slice1..8 and alphanumeric revision')
frozen=[json.loads(x) for x in (w/'private/freeze/BLIND_AUDIT_PACKET_PRIVATE.jsonl').read_text().splitlines() if x.strip()]
if len(frozen)!=153:
    raise RuntimeError('frozen audit record count differs from accepted receipt')
selected=frozen[20*(n-1):20*n]
out=w/('private/validation/audit%03d_%s'%(n,revision));out.mkdir(parents=True,exist_ok=True)
packet=out/'AUDIT_ASSIGNED_SLICE_PRIVATE.jsonl'
packet.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in selected))
assignment={'packet_id':'formal800-blind-audit-v1','packet_filename':packet.name,
 'review_filename':'AUDIT_%03d_SOL_HIGH.jsonl'%n,'model':'gpt-5.6-sol','effort':'high',
 'agent_id':'/root/formal800_audit_sol','role':'blind_audit'}
assign=out/'ASSIGNMENT_PRIVATE.jsonl';assign.write_text(json.dumps(assignment)+'\n')
subprocess.run([sys.executable,str(w/'code/run_review_validation.py'),'--assignments',str(assign),
 '--packet-dir',str(out),'--review-dir',str(w/'private/reviews'),
 '--schema',str(w/'code/FORMAL800_REVIEW_SCHEMA.json'),'--output-dir',str(out)],check=True)
PY
