#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-10-f
#
# Single job: venv rebuild attempt 2. Payload d/e found no `module` command —
# cron shells are non-login, so SCC's module system (loaded via /etc/profile)
# never initializes. Fix: do the module work inside `bash -lc` (login shell).
# Safety unchanged: build to .venv-new, verify imports + selfcheck, swap only
# on success — a broken .venv would brick the cron.

echo "== python3 modules visible from a login shell =="
bash -lc 'module -t avail python3 2>&1 | grep -i "^python3" | sort -V | tail -5' \
  || echo "module still unavailable even in a login shell"

NEWEST=$(bash -lc 'module -t avail python3 2>&1 | grep -E "^python3/3\.[0-9]" | sort -V | tail -1')
echo "picked: ${NEWEST:-none}"

if [ -n "$NEWEST" ]; then
  rm -rf .venv-new
  bash -lc "module load $NEWEST && python3 --version && python3 -m venv $PWD/.venv-new" \
    && .venv-new/bin/pip install -q --upgrade pip \
    && .venv-new/bin/pip install -q pyyaml pandas pyarrow requests pytest \
    && .venv-new/bin/python -c "import yaml,pandas,pyarrow,requests; print('deps OK')" \
    && .venv-new/bin/python ops/runner/selfcheck.py \
    && rm -rf .venv-old && mv .venv .venv-old && mv .venv-new .venv \
    && echo "VENV SWAPPED to $(.venv/bin/python --version 2>&1) (old kept at .venv-old)" \
    || echo "VENV REBUILD FAILED — keeping the old 3.6 venv (see errors above)"
else
  echo "SKIP: no python3 module found; needs an interactive look at 'module avail' on the SCC"
fi

echo "== sanity: the cron's python still works =="
.venv/bin/python -c "import yaml; print('cron python OK:', __import__('sys').version.split()[0])"
