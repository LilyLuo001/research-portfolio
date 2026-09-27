#!/usr/bin/env python3
"""V6 binding for the verified compact-v2 storage implementation."""
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "stage_c_compact_v2" / "compact_candidate_batch.py"
SPEC = importlib.util.spec_from_file_location("compact_v2_base", str(BASE))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MODULE.RUNNER_VERSION = "bounded-v6-compact-v2"
MODULE.FROZEN_PARSER_SHA256 = "d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744"

if __name__ == "__main__":
    raise SystemExit(MODULE.main())
