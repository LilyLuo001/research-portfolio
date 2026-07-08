#!/usr/bin/env python3
"""lineage.py — emit the lineage JSON every brief's definition-of-done demands
(inputs, hashes, code version, timestamp). One helper, zero dependencies, so no
task has an excuse to skip it.

  python ops/runner/lineage.py <output-file> <input-file> [<input-file> ...]

writes <output-file>.lineage.json next to the output. Or from task code:

  from lineage import write_lineage
  write_lineage("p1/conv_exposure.parquet", ["p1/events_merged.csv"])
"""
import hashlib, json, pathlib, subprocess, sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_rev():
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def write_lineage(output, inputs, extra=None):
    """Write <output>.lineage.json describing how `output` was produced."""
    out = pathlib.Path(output)
    rec = {
        "output": str(out),
        "output_sha256": _sha256(out) if out.is_file() else None,
        "inputs": [{"path": str(i),
                    "sha256": _sha256(i) if pathlib.Path(i).is_file() else None,
                    "rows": None}
                   for i in inputs],
        "code_version": _git_rev(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        rec.update(extra)
    lp = out.with_name(out.name + ".lineage.json")
    lp.write_text(json.dumps(rec, indent=2) + "\n")
    return lp


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    print(f"wrote {write_lineage(sys.argv[1], sys.argv[2:])}")
