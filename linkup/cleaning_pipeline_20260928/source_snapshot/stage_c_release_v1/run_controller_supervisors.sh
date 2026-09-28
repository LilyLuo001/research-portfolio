#!/bin/bash
set -u
PY=/public/software/apps/python/3.8.10/bin/python3
ROOT=/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1
STATE=/public/home/lilysharp/linkup_release_v1
deadline=$(( $(date +%s) + 432000 ))

while [ "$(date +%s)" -lt "$deadline" ]; do
  if [ -f "$STATE/disposition_prep_v1/continuation/COMPLETE.json" ]; then break; fi
  "$PY" "$ROOT/prep_server_continuation.py" >> "$STATE/disposition_prep_v1/continuation/controller-supervisor.log" 2>&1 || true
  sleep 60
done

while [ "$(date +%s)" -lt "$deadline" ]; do
  if [ -f "$STATE/semantic_v1/ALL_REGIONS_PUBLISHED_COMPLETE.json" ]; then break; fi
  "$PY" "$ROOT/semantic_server_controller.py" >> "$STATE/semantic_v1/semantic-controller-supervisor.log" 2>&1 || true
  sleep 60
done
