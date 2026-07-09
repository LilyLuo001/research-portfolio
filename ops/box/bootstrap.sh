#!/usr/bin/env bash
# bootstrap.sh — stand up the always-on L0/L1 box in one command.
#
# Idempotent and safe to re-run. Does clone -> venv -> deps -> .env scaffold ->
# sentinel-fenced smoke test -> (optional) cron install. Holds NO Claude
# credential and never drives a subscription (see ops/COMPLIANCE.md); it runs
# only your own scripts + the cheap non-Anthropic APIs.
#
# Usage:
#   # from anywhere, cloning fresh:
#   REPO_URL=git@github.com:you/research-portfolio.git ops/box/bootstrap.sh
#   # or from inside an existing checkout (uses it, pulls latest):
#   ops/box/bootstrap.sh
#   # also install the cron schedule (merges into your crontab, idempotent):
#   INSTALL_CRON=1 ops/box/bootstrap.sh
#
# Config (args or env):
#   REPO_URL     git URL to clone if no checkout is found      (optional)
#   TARGET_DIR   where to clone / find the repo   (default: $HOME/portfolio)
#   INSTALL_CRON =1 to merge the cron schedule into your crontab (default: off)
set -euo pipefail

REPO_URL="${1:-${REPO_URL:-}}"
TARGET_DIR="${2:-${TARGET_DIR:-$HOME/portfolio}}"
INSTALL_CRON="${INSTALL_CRON:-}"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# --- 1. locate or clone the repo -------------------------------------------
if [ -e "$TARGET_DIR/.git" ]; then
  ROOT="$TARGET_DIR"
  say "using existing checkout at $ROOT (pulling latest)"
  git -C "$ROOT" pull --ff-only || echo "   (skipped pull — resolve manually if needed)"
elif [ -n "$REPO_URL" ]; then
  say "cloning $REPO_URL -> $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
  ROOT="$TARGET_DIR"
elif ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  say "using the checkout this script lives in: $ROOT"
else
  echo "ERROR: no checkout found and no REPO_URL given." >&2
  echo "  run:  REPO_URL=<git url> $0" >&2
  exit 1
fi

# the repo root IS the project root
PROJECT="$ROOT"
[ -f "$PROJECT/ops/runner/runner.py" ] || { echo "ERROR: $PROJECT is not the portfolio repo"; exit 1; }
cd "$PROJECT"

# --- 2. virtualenv + dependencies ------------------------------------------
say "creating/using virtualenv (.venv) and installing dependencies"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyyaml pandas pyarrow requests
echo "   deps ready: $(python -c 'import yaml,pandas,pyarrow,requests; print("pyyaml pandas pyarrow requests")')"

# --- 3. L1 keys (box-only, git-ignored) — hidden entry via setkeys.sh -------
if [ ! -f ops/box/.env ]; then
  if [ -t 0 ]; then
    say "let's enter your L1 API keys now (hidden input)"
    bash ops/box/setkeys.sh
  else
    cp ops/box/env.example ops/box/.env
    say "created ops/box/.env from the template (non-interactive shell)"
    echo "   >>> run  ops/box/setkeys.sh  to enter your keys with hidden prompts."
  fi
else
  echo "   ops/box/.env already present — run ops/box/setkeys.sh to add/rotate keys."
fi
git check-ignore -q ops/box/.env && echo "   (.env is git-ignored — good)" || \
  echo "   WARNING: ops/box/.env is NOT git-ignored — do not commit it!"

# --- 4. prove the L1 layer (sentinel-fenced smoke, keyless) -----------------
say "smoke-testing the L1 dispatch layer (SH-l1-smoke)"
set -a; . ops/box/.env 2>/dev/null || true; set +a
python ops/runner/dispatch.py --smoke
echo "   worker key status:"; python ops/runner/dispatch.py --workers | sed 's/^/     /'

# --- 5. git identity for the box's brief/digest commits --------------------
if ! git config user.email >/dev/null 2>&1; then
  git config user.email "portfolio-box@localhost"
  git config user.name  "portfolio-box"
  say "set a placeholder git identity — change it to yours:"
  echo "   git config user.email you@example.com && git config user.name 'you'"
fi

# --- 6. cron schedule -------------------------------------------------------
VENV_PY="$PROJECT/.venv/bin/python"
MARK="# portfolio-box (managed by bootstrap.sh)"
read -r -d '' CRON_BLOCK <<EOF || true
$MARK
*/30 * * * *  cd $PROJECT && git pull --ff-only -q origin main >> ops/box/cron.log 2>&1; cd $PROJECT && $VENV_PY ops/runner/runner.py --apply-decisions >> ops/box/cron.log 2>&1; cd $PROJECT && $VENV_PY ops/runner/runner.py --reap >> ops/box/cron.log 2>&1; cd $PROJECT && bash ops/box/run_inbox.sh >> ops/box/cron.log 2>&1
0 2 * * *     cd $PROJECT && set -a && . ops/box/.env && set +a && $VENV_PY ops/runner/l1_driver.py --live >> ops/box/cron.log 2>&1
0 21 * * *    cd $PROJECT && $VENV_PY ops/runner/runner.py --digest >> ops/box/cron.log 2>&1 && git add ops/briefs ops/digest ops/runner/state.json ops/decisions.md ops/l1/out && git commit -q -m "box: nightly digest \$(date +\%F)" && git push -q origin HEAD:main >> ops/box/cron.log 2>&1
$MARK-end
EOF

if [ "$INSTALL_CRON" = "1" ]; then
  say "installing cron schedule (idempotent — replaces the managed block)"
  existing="$(crontab -l 2>/dev/null || true)"
  if printf '%s\n' "$existing" | grep -qF "$MARK"; then
    # strip the old managed block so schedule updates actually deploy
    existing="$(printf '%s\n' "$existing" \
      | awk -v s="$MARK" -v e="$MARK-end" '$0==s{skip=1} !skip{print} $0==e{skip=0}')"
    echo "   replacing existing managed block"
  fi
  { printf '%s\n' "$existing"; printf '%s\n' "$CRON_BLOCK"; } | crontab -
  echo "   installed. verify with: crontab -l"
else
  say "cron schedule (resolved to this box) — install with INSTALL_CRON=1, or paste into 'crontab -e':"
  printf '%s\n' "$CRON_BLOCK" | sed 's/^/   /'
fi

say "box bootstrap complete."
cat <<EOF
Next:
  1. Fill L1 keys:   \$EDITOR $PROJECT/ops/box/.env    (then re-run --smoke)
  2. Go live:        wire the real POST in ops/runner/models.py, run one live batch
  3. Schedule it:    INSTALL_CRON=1 $0        (if you skipped cron above)
  4. Daily:          make plan   (morning)  /   make digest  (evening)
The box holds no Claude credential; L2 work happens in the official apps on your seats.
EOF
