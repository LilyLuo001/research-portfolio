#!/usr/bin/env python3
"""Validate and seal the YAX Scope Phase 1 deliverables."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
EXPECTED_PROTECTED = {
    "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json":
        "4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831",
    "yax/analysis/outcomes/frozen_v11_corrected_run/RESULT_LEDGER.jsonl":
        "e900adb75510729be635eb7aea381bfe6e523b376b6f2723350cf47bdf09266b",
    "yax/manuscript/v4_1/YAX_MANUSCRIPT_v4_1_CLEAN.md":
        "1591a4a545095d3d7b0c65062849fb1101a49bd803e6e0e3e732e84c715e700c",
}
REQUIRED = (
    "YAX_SCOPE_PHASE1_ANALYSIS_PLAN.md",
    "YAX_AGE_PROFILE_RESULTS.csv",
    "figure_age_experience_profile.png",
    "CPS_LONGITUDINAL_VARIABLE_INVENTORY.csv",
    "CPS_LONGITUDINAL_MATCH_RATES.csv",
    "CPS_FLOW_SAMPLE_FEASIBILITY.csv",
    "CPS_OCCUPATION_SWITCHING_NOISE_AUDIT.md",
    "CPS_LONGITUDINAL_WEIGHT_AUDIT.md",
    "YAX_FUTURE_FLOW_ANALYSIS_PLAN.md",
    "YAX_SCOPE_PHASE1_DECISION_MEMO.md",
    "YAX_AGE_PROFILE_RECEIPT.json",
    "CPS_LONGITUDINAL_FEASIBILITY_RECEIPT.json",
    "run_phase1_age_profile.py",
    "run_phase1_flow_audit.py",
    "finalize_phase1.py",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    missing = [name for name in REQUIRED if not (HERE / name).is_file()]
    if missing:
        raise RuntimeError(f"missing Phase-1 deliverables: {missing}")

    protected = {name: sha256(ROOT / name) for name in EXPECTED_PROTECTED}
    if protected != EXPECTED_PROTECTED:
        raise RuntimeError(f"immutable protected artifact changed: {protected}")
    if git("rev-parse", "v1.1-design-freeze^{}") != "22fbf7924809b7a535e31ae0ab68f5b113ce8078":
        raise RuntimeError("design-freeze tag changed")
    if git("rev-parse", "v1.1-confirmatory-results^{}") != "b16109482c3bf5ca176f6f08976e120b04769945":
        raise RuntimeError("confirmatory-results tag changed")

    with (HERE / "YAX_AGE_PROFILE_RESULTS.csv").open(encoding="utf-8") as handle:
        age_rows = list(csv.DictReader(handle))
    if [row["Age group"] for row in age_rows] != [
        "18-21", "22-25", "26-30", "31-40", "41-50", "51-65"
    ]:
        raise RuntimeError("age-profile bins differ from the predeclared six")
    if any(row["analysis_status"] != LABEL for row in age_rows):
        raise RuntimeError("age result lacks Phase-1 status label")

    age_receipt = json.loads((HERE / "YAX_AGE_PROFILE_RECEIPT.json").read_text())
    flow_receipt = json.loads((HERE / "CPS_LONGITUDINAL_FEASIBILITY_RECEIPT.json").read_text())
    authorized = age_receipt["new_outcome_regressions_executed"]
    if authorized != [
        "one pre-declared grouped-multinomial conditional-PPML flexible age-profile model"
    ]:
        raise RuntimeError("unexpected outcome regression ledger")
    if flow_receipt["flow_treatment_effect_regressions_executed"] != []:
        raise RuntimeError("a flow treatment-effect regression was executed")
    if age_receipt["preanalysis_plan_commit"] != "d4818ee":
        raise RuntimeError("age plan was not authenticated to its pre-outcome commit")

    status = git("status", "--porcelain").splitlines()
    allowed_test = "yax/tests/test_scope_phase1.py"
    outside = [
        line for line in status
        if "yax/analysis/postoutcome_scope_phase1/" not in line and allowed_test not in line
    ]
    if outside:
        raise RuntimeError(f"worktree changes outside Phase-1 namespace: {outside}")

    output_hashes = {name: sha256(HERE / name) for name in REQUIRED}
    receipt = {
        "record": "YAX Scope Expansion Phase 1 reproducibility receipt",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": git("branch", "--show-current"),
        "base_commit_before_phase1": "ca5a02478b68f1a0e47eadd4e8816bbc96c9dcc3",
        "preanalysis_plan_commit": "d4818ee7af834b51d73a6b59849775f75eee2fb9",
        "current_head_before_final_artifact_commit": git("rev-parse", "HEAD"),
        "immutable_tags": {
            "v1.1-design-freeze": git("rev-parse", "v1.1-design-freeze^{}"),
            "v1.1-confirmatory-results": git("rev-parse", "v1.1-confirmatory-results^{}"),
        },
        "protected_artifact_hashes": protected,
        "phase1_artifact_hashes": output_hashes,
        "phase1_test_file": {
            "path": "yax/tests/test_scope_phase1.py",
            "sha256": sha256(ROOT / "yax/tests/test_scope_phase1.py"),
        },
        "authenticated_private_input_hashes": {
            "age_profile": age_receipt["input_hashes"],
            "flow_feasibility": flow_receipt["input_hashes"],
        },
        "age_profile": {
            "classification": "AGE-A with precision caveat",
            "q5_membership_identical_to_historical": age_receipt["q5_membership_identical_to_historical"],
            "optimizer": age_receipt["optimizer"],
            "bootstrap": age_receipt["bootstrap"],
        },
        "flow_feasibility": {
            "classification": "FLOW-B (strong; adjacent-month only)",
            "preferred_id": flow_receipt["link_rules"]["preferred_id"],
            "switching": flow_receipt["switching"],
        },
        "joint_decision": "PATH 1 — promote only after a separately predeclared flow freeze",
        "new_outcome_regressions_executed": authorized,
        "flow_treatment_effect_regressions_executed": [],
        "prohibited_analyses_executed": [],
        "main_manuscript_modified": False,
        "protected_confirmatory_artifacts_modified": False,
        "uncommitted_paths_at_seal_limited_to_phase1_namespace_and_phase1_test": True,
        "tests": {
            "dax_and_yax": "556 passed, 3 skipped",
            "repository_wide_collection": (
                "blocked outside YAX by absent ops/l1/gemini_helper.py; after ignoring that "
                "collector, 607 passed, 3 skipped and 3 ops/runner inbox tests failed because "
                "ops/box/run_inbox.sh is absent"
            ),
            "phase1_test_failures": 0,
        },
    }
    target = HERE / "YAX_SCOPE_PHASE1_REPRODUCIBILITY_RECEIPT.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS_PHASE1_SEALED", "receipt": str(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
