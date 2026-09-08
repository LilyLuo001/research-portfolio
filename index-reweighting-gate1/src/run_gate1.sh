#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/USMPD.xlsx" >&2
  exit 2
fi

GATE1_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USMPD_XLSX="$1"

if [[ ! -f "$USMPD_XLSX" ]]; then
  echo "USMPD workbook not found: $USMPD_XLSX" >&2
  exit 2
fi

cd "$GATE1_ROOT"
python3 src/build_rule_registry.py
python3 src/build_fomc_calendar.py --usmpd-xlsx "$USMPD_XLSX"
python3 src/build_design_audit.py
python3 src/summarize_gate1.py
python3 -m pytest -q
python3 src/validate_gate1.py
