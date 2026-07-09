#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-09-d
#
# Previous cycle (f922899): cron dedupe confirmed; KIMI_MODEL pinned; kimi
# then 400'd with "invalid temperature: only 1 is allowed for this model" —
# fixed in models.py this same push (K2 models get temperature=1).
# This payload: (1) rebuild the venv on Python 3.10+ (current 3.6.8 breaks
# subprocess capture_output in contracts/lease/lineage), SAFELY: build to
# .venv-new, verify, swap only on success — a broken .venv bricks the cron;
# (2) rerun the live pass with the temperature fix.

echo "== python venv upgrade (3.6.8 -> newest module python3) =="
source /etc/profile.d/modules.sh 2>/dev/null || source /usr/share/Modules/init/bash 2>/dev/null || true
if type module >/dev/null 2>&1; then
  NEWEST=$(module -t avail python3 2>&1 | grep -E '^python3/3\.(1[0-9]|[2-9][0-9])' | sort -V | tail -1)
  echo "newest python3 module: ${NEWEST:-none found}"
  if [ -n "$NEWEST" ]; then
    module load "$NEWEST"
    python3 --version
    rm -rf .venv-new
    python3 -m venv .venv-new \
      && .venv-new/bin/pip install -q --upgrade pip \
      && .venv-new/bin/pip install -q pyyaml pandas pyarrow requests pytest \
      && .venv-new/bin/python -c "import yaml,pandas,pyarrow,requests; print('deps OK')" \
      && .venv-new/bin/python ops/runner/selfcheck.py \
      && rm -rf .venv-old && mv .venv .venv-old && mv .venv-new .venv \
      && echo "VENV SWAPPED to $(.venv/bin/python --version 2>&1) (old kept at .venv-old)" \
      || echo "VENV REBUILD FAILED — keeping the old 3.6 venv (see errors above)"
  fi
else
  echo "module system not available in this shell — venv upgrade needs an interactive look"
fi

echo "== live L1 pass (kimi-k2.6, temperature fix from this same pull) =="
.venv/bin/python ops/runner/l1_driver.py --live

echo "== capture any new DONE outputs =="
git add -f ops/l1/out/*.json 2>/dev/null || true

echo "== night report =="
cat ops/l1/out/_last_night.json 2>/dev/null || true
