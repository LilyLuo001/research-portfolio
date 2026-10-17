#!/bin/bash
# Login-node coordination only: readiness checks, sbatch submission, sacct polling.
set -eu
T=/work/home/lilysharp/private/fixed10k_semantic_production_20261017
C="$T/private/continuation"
exec 9>"$C/receipts/CONTROLLER.lock"
if ! flock -n 9; then
  echo "another continuation controller holds the lock" >&2
  exit 3
fi
echo "$$" > "$C/receipts/CONTROLLER.pid"
exec python3 "$C/code/continuation_controller.py" --root "$T" --first-batch 5 --last-batch 69 --poll-seconds 30 --max-idle-seconds 42000 --receipt "$C/receipts/CONTROLLER_RECEIPT.json"
