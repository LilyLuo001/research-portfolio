#!/usr/bin/env bash
# inbox.sh — commands for the box's next 30-min cycle (see run_inbox.sh).
# inbox-version: 2026-07-10-g
#
# Two jobs, both idempotent:
#   (1) payload-f venv rebuild, kept but GUARDED — skipped once the cron venv
#       is already >= 3.7 (so this payload is safe whether or not f ran).
#   (2) NEW: launch the P1 EDGAR filing-package harvester (L0, deterministic)
#       detached — it is THE unlock for all four post-gate overnight batches
#       (P1-T1-events A/B, P1-T13-ant A/B; see p1/fetch_edgar_filings.py
#       docstring). Gate P1-GATE-t2a passed 2026-07-10, so this starts now.
#       Raw .htm filings are gitignored (box-local); only manifest.csv is
#       committed by later ticks.

# ---- (1) venv rebuild, only if still on < 3.7 -------------------------------
if .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3,7) else 1)'; then
  echo "venv already $(.venv/bin/python --version 2>&1) — rebuild skipped"
else
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
fi

echo "== sanity: the cron's python still works =="
.venv/bin/python -c "import yaml; print('cron python OK:', __import__('sys').version.split()[0])"

# ---- (2) EDGAR harvester launch (detached, resumable) -----------------------
echo "== P1 EDGAR harvester =="
PIDFILE=p1/edgar_filings/.harvest.pid
mkdir -p p1/edgar_filings
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "harvester already running (pid $(cat "$PIDFILE")) — not restarting"
  tail -3 p1/edgar_filings/harvest.log 2>/dev/null
elif [ -z "${EDGAR_CONTACT:-}" ]; then
  echo "NEED_HUMAN: EDGAR_CONTACT is not set — add 'EDGAR_CONTACT=<your email>'"
  echo "to ops/box/.env (box-local, gitignored; SEC fair-use requires it)."
  echo "Harvester NOT started; this payload re-checks on nothing — bump the"
  echo "inbox-version after adding the var, or start by hand:"
  echo "  setsid nohup .venv/bin/python p1/fetch_edgar_filings.py >> p1/edgar_filings/harvest.log 2>&1 &"
else
  setsid nohup .venv/bin/python p1/fetch_edgar_filings.py \
    >> p1/edgar_filings/harvest.log 2>&1 &
  echo $! > "$PIDFILE"
  echo "harvester STARTED detached (pid $(cat "$PIDFILE")) — idempotent/resumable;"
  echo "manifest lands at p1/edgar_filings/manifest.csv (the only git-tracked file)."
  sleep 5; tail -5 p1/edgar_filings/harvest.log 2>/dev/null
fi
