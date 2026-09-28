#!/bin/bash
# One allocation processes the remaining 15 prefixes sequentially.  Each
# prefix retains its own immutable receipt and can be resumed by the same CLI.
#SBATCH --job-name=linkup-disp-remaining-v1
#SBATCH --partition=kshctest02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=96G
#SBATCH --time=1-00:00:00
#SBATCH --output=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-remaining-%j.out
#SBATCH --error=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1/logs/disposition-remaining-%j.err
set -euo pipefail
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
OUT=/public/home/lilysharp/linkup_release_v1/disposition_prep_v1
export PYTHONPATH=/public/home/lilysharp/linkup_analysis_v1/stage_b/runtime_py38
SCRATCH_A=/public/home/lilysharp/linkup_release_v1/disposition_prep_v1_scratch
SCRATCH_B=/public/home/lilysharp/linkup_release_v1/disposition_ducktemp_v1
FRAGMENT_CAP=16000000000
SCRATCH_CAP=2000000000
FREE_RESERVE=8000000000
for prefix in 1 2 3 4 5 6 7 8 9 a b c d e f; do
  /public/software/apps/python/3.8.10/bin/python3 "${ROOT}/prepare_release_dispositions.py" prefix \
    --config "${ROOT}/config_disposition_kunshan.json" --prefix "${prefix}" &
  child=$!
  while kill -0 "${child}" 2>/dev/null; do
    fragment_bytes=$(du -sb "${OUT}/prefix_fragments" "${OUT}/prefix_attempts" 2>/dev/null | awk '{s+=$1} END {print s+0}')
    scratch_bytes=$(du -sb "${SCRATCH_A}" "${SCRATCH_B}" 2>/dev/null | awk '{s+=$1} END {print s+0}')
    free_bytes=$(df -PB1 /public/home/lilysharp/linkup_release_v1 | awk 'NR==2 {print $4}')
    if (( fragment_bytes > FRAGMENT_CAP || scratch_bytes > SCRATCH_CAP || free_bytes < FREE_RESERVE )); then
      echo "bounded storage guard stopped prefix ${prefix}: fragments=${fragment_bytes} scratch=${scratch_bytes} free=${free_bytes}" >&2
      kill -TERM "${child}" 2>/dev/null || true
      sleep 10
      kill -KILL "${child}" 2>/dev/null || true
      wait "${child}" || true
      exit 75
    fi
    sleep 30
  done
  wait "${child}"
done
/public/software/apps/python/3.8.10/bin/python3 - <<'PY'
import json, os
from pathlib import Path
root = Path('/public/home/lilysharp/linkup_release_v1/disposition_prep_v1')
receipts = [json.loads((root/'prefix_receipts'/('prefix_%s.json' % p)).read_text())
            for p in '0123456789abcdef']
if any(x.get('status') != 'complete' or not x.get('row_conservation') for x in receipts):
    raise RuntimeError('prefix receipt set is incomplete')
if sum(x['occurrence_rows'] for x in receipts) != 164581116 + 134091962:
    raise RuntimeError('global occurrence conservation failed')
value = {'status':'complete', 'prefixes':'0123456789abcdef',
         'occurrence_rows':sum(x['occurrence_rows'] for x in receipts),
         'fragment_bytes':sum(y['bytes'] for x in receipts for y in x['fragment_files']),
         'script_sha256':receipts[0]['script_sha256'],
         'config_sha256':receipts[0]['config_sha256']}
path = root/'REMAINING_PREFIXES_COMPLETE.json'; temp = Path(str(path)+'.tmp')
temp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n'); os.replace(temp, path)
PY
