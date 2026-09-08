#!/usr/bin/env bash
set -euo pipefail

: "${YAX_REPO_ROOT:?set YAX_REPO_ROOT to an SCC checkout}"
: "${YAX_ACS_DATA_ROOT:?set YAX_ACS_DATA_ROOT under /projectnb/econdept}"
: "${YAX_V3_RUN_ROOT:?set YAX_V3_RUN_ROOT under /projectnb/econdept}"
: "${YAX_PYTHON_BIN:=python3}"

case "$YAX_ACS_DATA_ROOT" in /projectnb/econdept/*) ;; *) exit 2 ;; esac
case "$YAX_V3_RUN_ROOT" in /projectnb/econdept/*) ;; *) exit 2 ;; esac

out="$YAX_V3_RUN_ROOT/gate4_acs_extension_$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$out"

"$YAX_PYTHON_BIN" \
  "$YAX_REPO_ROOT/yax/revision/substantive_v3_20260906/gate4/acs_extension/run_acs_extension.py" \
  --acs-dir "$YAX_ACS_DATA_ROOT" \
  --bridge "$YAX_REPO_ROOT/yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv" \
  --primary-membership "$YAX_REPO_ROOT/yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv" \
  --broader-membership "$YAX_REPO_ROOT/yax/revision/substantive_v3_20260906/runs/gate2_broader_support_authoritative_20260908/BROADER_SUPPORT_MEMBERSHIP.csv" \
  --output-dir "$out"

"$YAX_PYTHON_BIN" \
  "$YAX_REPO_ROOT/yax/revision/substantive_v3_20260906/gate4/acs_extension/validate_acs_extension_outputs.py" \
  --output-dir "$out"

