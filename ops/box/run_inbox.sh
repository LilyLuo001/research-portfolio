#!/usr/bin/env bash
# run_inbox.sh — the box's "remote hands": execute ops/box/inbox.sh ONCE per
# new version and push the output back to main.
#
# Loop: an operator (human or Claude session) edits ops/box/inbox.sh and merges
# it to main -> the box's 30-min cron pulls and calls this script -> it sees a
# new inbox hash, runs it (with L1 keys loaded, repo root as cwd, venv python
# first on PATH), appends stdout+stderr to ops/box/inbox_log.md (tracked), and
# commits + pushes so the operator can read the result from the repo. Re-runs
# of the SAME inbox content are no-ops (hash marker in ops/box/.inbox_done,
# untracked) — re-arm by changing the inbox file (a comment line is enough).
#
# SECURITY: this executes shell from the repo. Anyone with push access to main
# can run commands on the box — the same trust boundary as the existing cron
# (which already executes repo Python), accepted explicitly by the owner
# 2026-07-09. Keep the repo private and its collaborator list short.
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
INBOX=ops/box/inbox.sh
MARK=ops/box/.inbox_done
LOG=ops/box/inbox_log.md
TIMEOUT_S=1500   # < the 30-min cron cadence, so runs never pile up

[ -f "$INBOX" ] || exit 0
hash="$(sha256sum "$INBOX" | cut -d' ' -f1)"
[ -f "$MARK" ] && [ "$(cat "$MARK")" = "$hash" ] && exit 0
# mark BEFORE running: a crashing/hanging inbox must not re-run every 30 min
echo "$hash" > "$MARK"

{
  echo ""
  echo "## $(date -u +%FT%TZ) — inbox ${hash:0:12} @ git $(git rev-parse --short HEAD 2>/dev/null || echo none)"
  echo '```'
  set -a; . ops/box/.env 2>/dev/null || true; set +a
  PATH="$ROOT/.venv/bin:$PATH" timeout "$TIMEOUT_S" bash "$INBOX" 2>&1
  echo "[exit: $?]"
  echo '```'
} >> "$LOG"

git add -A
git commit -q -m "box: inbox run $(date -u +%FT%TZ)" || true
git push -q origin HEAD:main \
  || { git pull --rebase -q origin main && git push -q origin HEAD:main; } \
  || true
