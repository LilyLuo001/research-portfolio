"""Validate and bind this small public package; never access the raw archive."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "PUBLICATION_RECEIPT.json"
PRIVATE_LOCAL = ["AUTHORITATIVE_SUPPORT_GATE.json", "DESIGN_MATRIX_DIAGNOSTICS.json",
                 "metadata/DESIGN_MATRIX_DIAGNOSTICS.json"]
PRIVATE_BOUND = {"AUTHORITATIVE_SUPPORT_GATE.json", "receiver_event_design.parquet",
                 "control_assignment.parquet"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not any((ROOT / name).exists() for name in PRIVATE_LOCAL)
    for name in ["README.md", "DECISION.md", "INDEPENDENT_REVIEW.md", "SPEC_FROZEN.json",
                 "REPLICATION_RESULTS.csv", "SENSITIVITY_RESULTS.csv", "EXECUTION_RECEIPT.json"]:
        assert (ROOT / name).is_file(), name
    pre = json.loads((ROOT / "PREOUTCOME_REVIEW.json").read_text())
    checked = []
    for name, expected in pre["bound_sha256"].items():
        if name in PRIVATE_BOUND:
            continue
        p = ROOT / name
        if name == "build_result_blind_metadata.py":
            p = ROOT / "metadata" / name
        assert digest(p) == expected, name
        checked.append(name)
    execution = json.loads((ROOT / "EXECUTION_RECEIPT.json").read_text())
    for name, expected in execution["public_output_sha256"].items():
        assert digest(ROOT / name) == expected, name
    files = {}
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p == OUTPUT or "__pycache__" in p.parts:
            continue
        assert p.suffix not in {".parquet", ".dbn", ".zst", ".gz"}, p
        assert p.stat().st_size < 5_000_000, p
        files[str(p.relative_to(ROOT))] = {"sha256": digest(p), "bytes": p.stat().st_size}
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "2514b9a7db014eaa2d7324d189c3b5f6c609c04e",
        "scientific_action": "INCONCLUSIVE_STOP_SPENDING",
        "independent_review": "See final INDEPENDENT_REVIEW.md; computation pass is not research GO",
        "unchanged_local_preoutcome_bindings_checked": checked,
        "private_preoutcome_bindings": "SCC-only; independently checked by referee; local copies not published",
        "raw_archive_scanned": False,
        "files": files,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files_bound": len(files), "local_preoutcome_bindings_checked": len(checked)}))


if __name__ == "__main__":
    main()
