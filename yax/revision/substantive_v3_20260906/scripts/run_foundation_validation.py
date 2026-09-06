#!/usr/bin/env python3
"""Run and receipt the nonempirical V3 foundation checks."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def code_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(REPO)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def public_command(command: list[str]) -> list[str]:
    """Remove machine-specific paths from a versioned validation receipt."""
    result = []
    repo_text = str(REPO)
    for token in command:
        if token == sys.executable:
            result.append("<YAX_PYTHON_BIN>")
        elif token == repo_text:
            result.append("<YAX_REPO_ROOT>")
        elif token.startswith(repo_text + "/"):
            result.append("<YAX_REPO_ROOT>/" + token[len(repo_text) + 1:])
        else:
            result.append(token)
    return result


def main() -> int:
    script_paths = sorted((ROOT / "scripts").glob("*.py"))
    test_paths = sorted((ROOT / "tests").glob("test_*.py"))
    combined_hash = code_digest(script_paths + test_paths)
    spec = ROOT / "contracts/specs/canonical_baseline_reproduction.json"
    with spec.open("r", encoding="utf-8") as stream:
        spec_id = json.load(stream)["spec_id"]
    commands = [
        [sys.executable, str(ROOT / "scripts/spec_contract.py"), "validate", str(spec)],
        [sys.executable, str(ROOT / "scripts/dependency_guard.py"),
         str(ROOT / "contracts/run_manifest.json"), "--root", str(ROOT)],
        [sys.executable, str(ROOT / "scripts/validate_claim_ledger.py"),
         "--results", str(ROOT / "contracts/result_ledger.json"),
         "--claims", str(ROOT / "contracts/claim_ledger.json"), "--root", str(ROOT)],
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"),
         "-p", "test_*.py", "-v"],
    ]
    run_dir = ROOT / "runs/foundation"
    gate_dir = ROOT / "gates"
    run_dir.mkdir(parents=True, exist_ok=True)
    gate_dir.mkdir(parents=True, exist_ok=True)
    started = now()
    checks = []
    overall = 0
    for command in commands:
        completed = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        checks.append({
            "command": public_command(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
        if completed.returncode != 0:
            overall = 1
    ended = now()
    report = {
        "schema_version": "yax-v3-foundation-validation-v1",
        "status": "PASS" if overall == 0 else "FAIL",
        "scientific_validity": "not determined; these are contract-integrity tests",
        "spec_id": spec_id,
        "code_hash": combined_hash,
        "checks": checks,
    }
    report_path = gate_dir / "FOUNDATION_VALIDATION.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "command": f"<YAX_PYTHON_BIN> {Path(__file__).relative_to(REPO)}",
        "start_utc": started,
        "end_utc": ended,
        "exit_code": overall,
        "mode": "engineering_validation",
        "code_hash": combined_hash,
        "spec_id": spec_id,
        "output_hashes": {
            str(report_path.relative_to(ROOT)): sha256(report_path),
            str(spec.relative_to(ROOT)): sha256(spec),
            "ACCEPTANCE_CHECK_CROSSWALK.csv": sha256(ROOT / "ACCEPTANCE_CHECK_CROSSWALK.csv"),
        },
        "note": "No empirical analysis or protected-data read occurred in this validation.",
    }
    receipt_path = run_dir / "EXECUTION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "receipt": str(receipt_path),
                      "validation": str(report_path)}, indent=2))
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
