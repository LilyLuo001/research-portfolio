"""Bind the small publication artifacts; never scan SCC or raw archives."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "ROUTING_AND_RUN_RECEIPT.json"


def main():
    required = ["README.md", "SPEC_AMENDMENT.md", "analysis_config.json",
                "PRECISION_AND_DECISION.md", "INDEPENDENT_REVIEW.md"]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("Missing final artifacts: " + ", ".join(missing))
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == RECEIPT or "__pycache__" in path.parts:
            continue
        if path.suffix in {".parquet", ".dbn", ".zst", ".gz"}:
            raise SystemExit("Unexpected bulk/raw-format artifact: " + str(path))
        if path.stat().st_size > 5_000_000:
            raise SystemExit("Unexpected large artifact: " + str(path))
        files[str(path.relative_to(ROOT))] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "4ee495f618494d847f2361e96d6fe103c04ebc37",
        "git_branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "observed_cli_version": "codex-cli 0.143.0",
        "requested_dispatch": {
            "scientific_executor": ["gpt-5.6-sol", "medium"],
            "intraday_engineer": ["gpt-5.6-terra", "medium"],
            "independent_referee": ["gpt-6-astra", "high"],
        },
        "backend_model_effort_telemetry": "NOT_OBSERVED",
        "dispatch_and_completion_evidence": "COORDINATION.md and INDEPENDENT_REVIEW.md",
        "scope": "Daily exploratory association and bounded intraday feasibility, not causal certification",
        "raw_location": "SCC only; see source-specific execution receipts",
        "hash_scope": "This small new publication directory only; no raw archive hash sweep",
        "artifact_files": files,
    }
    RECEIPT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files_bound": len(files), "receipt": str(RECEIPT)}))


if __name__ == "__main__":
    main()
