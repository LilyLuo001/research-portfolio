#!/bin/bash
set -euo pipefail

# SessionStart hook for Claude Code on the web. It gives the fresh cloud sandbox
# the Python packages the backbone needs so a seat can run contracts.py, the
# runner, and (once SH-econlib exists) the econlib tests without a cold "module
# not found" on the first command.
#
# Web-only: on your always-on box you manage your own venv, so this no-ops there.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# contracts.py -> pandas/pyarrow ; runner.py/lease.py -> pyyaml ; econlib -> pytest.
# Idempotent: pip is a fast no-op when the packages are already present, and the
# sandbox caches container state after the hook completes.
python -m pip install --quiet --disable-pip-version-check \
  pyyaml pandas pyarrow pytest

echo "portfolio backbone dependencies ready" >&2
