#!/usr/bin/env bash
set -euo pipefail

repo_root="${YAX_REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$repo_root"

python3 paper/scripts/build_r3_exhibits.py
python3 yax/revision/substantive_r3_20260905/dynamics/rebuilt_family_harmonization/selfcheck.py \
  --output-dir yax/revision/substantive_r3_20260905/dynamics/rebuilt_family_harmonization/results
python3 paper/scripts/audit_substantive_revision.py
python3 -m pytest -q

if command -v latexmk >/dev/null 2>&1; then
  make -C paper substantive-revision
fi
