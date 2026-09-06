#!/usr/bin/env python3
"""Seal the YAX Phase-2 result package after tests and result commit."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE = pathlib.Path(__file__).resolve().parent
LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
PHASE1_COMMIT = "0aefec9cf8837f33a09f4307c472ebc2ad75403a"
RESULT_PACKAGE_COMMIT = "8ebef7c4f443b5f9300ccfa7d1761f822215d790"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    if git("rev-parse", "HEAD") != RESULT_PACKAGE_COMMIT:
        raise RuntimeError("finalizer must run on the committed Phase-2 result package")
    protected = [
        "yax/analysis/outcomes", "yax/manuscript/v4", "yax/manuscript/v4_1",
        "yax/DESIGN_FREEZE_v2.md", "yax/analysis/FROZEN_RESULTS_REPORT.md",
    ]
    modified = git("diff", "--name-only", f"{PHASE1_COMMIT}..HEAD", "--", *protected)
    if modified:
        raise RuntimeError(f"protected prior state changed: {modified}")
    stage2a = json.loads((PHASE / "YAX_PHASE2_STAGE2A_RECEIPT.json").read_text())
    stage2c = json.loads((PHASE / "YAX_PHASE2_STAGE2C_RECEIPT.json").read_text())
    if stage2a["classification"] != "FLOW-M5" or stage2a["stage2B_authorized"]:
        raise RuntimeError("Stage-2A gate is not the recorded FLOW-M5 stop")
    if stage2c["stage2B_executed"]:
        raise RuntimeError("Stage 2B was unexpectedly executed")
    artifacts = {}
    for path in sorted(PHASE.iterdir()):
        if path.is_file() and path.name != "YAX_PHASE2_REPRODUCIBILITY_RECEIPT.json":
            artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    receipt = {
        "record": "YAX Phase 2 full reproducibility receipt",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "result_package_commit": RESULT_PACKAGE_COMMIT,
        "remote_branch": "origin/task/yax-phase2-20260831",
        "phase1_parent_commit": PHASE1_COMMIT,
        "immutable_refs": {
            "v1.1-design-freeze": git("rev-parse", "v1.1-design-freeze^{commit}"),
            "v1.1-confirmatory-results": git("rev-parse", "v1.1-confirmatory-results^{commit}"),
        },
        "protected_paths_changed_since_phase1": [],
        "phase15_status": json.loads((PHASE / "YAX_PHASE2_LONGITUDINAL_WEIGHT_RECEIPT.json").read_text())["status"],
        "phase2A_classification": stage2a["classification"],
        "phase2B_executed": False,
        "phase2C_executed_under_independent_predeclaration": True,
        "final_decision": "PATH-2B",
        "all_new_outcome_regressions_executed": [
            *stage2a["new_outcome_regressions_executed"],
            *stage2c["new_outcome_regressions_executed"],
        ],
        "all_excluded_analyses_executed": [],
        "long_gap_links_used": False,
        "tests": {
            "phase2_targeted": "10 passed",
            "core_DAX_YAX": "566 passed, 3 skipped in 4.20s",
            "bare_repository_pytest": "pre-existing collection failure: missing ops/l1/gemini_helper.py",
        },
        "artifacts": artifacts,
    }
    output = PHASE / "YAX_PHASE2_REPRODUCIBILITY_RECEIPT.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "SEALED", "artifacts": len(artifacts),
                      "regressions": len(receipt["all_new_outcome_regressions_executed"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
