#!/bin/bash
# Future-only submission wrapper. It was not used for the recorded jobs.
set -euo pipefail
: "${PHASE:?set PHASE=synthetic or pilot4}"
: "${EXPECTED_RECORDS:?set EXPECTED_RECORDS}"
BASE=/work/home/lilysharp/private/next_stage_20261004/local_inference_20261007/recovery
PROMPTS=${BASE}/private_eval/${PHASE}/prompts
python - "${PROMPTS}" <<'PY'
import pathlib, sys
paths = sorted(pathlib.Path(sys.argv[1]).glob("record_*.prompt.txt"))
if not paths:
    raise SystemExit("no prompt files")
bad = [path.name for path in paths if b"\x00" in path.read_bytes()]
if bad:
    raise SystemExit("embedded NUL is unsupported by the shell argument transport; refusing submission")
PY
PHASE=${PHASE} EXPECTED_RECORDS=${EXPECTED_RECORDS} sbatch --export=ALL,PHASE,EXPECTED_RECORDS \
  "${BASE}/run_private_phase_qwen3_wuzhen.sbatch"
