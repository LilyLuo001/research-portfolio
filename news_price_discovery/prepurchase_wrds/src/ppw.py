"""Shared locations, manifest access, and provenance helpers.

Every module in this package resolves its inputs through the manifest rather
than through hard-coded rescue filenames, because the archive's four raw trees
(`raw/`, `raw/maximal/`, `raw/rescue/`, `raw/rescue_remaining/`) hold
overlapping copies of the same logical table and the correct copy is a decision
to be made once, visibly, rather than implied by whichever path a notebook
happened to contain.

The baseline manifest was written before the final near-TAQ rescue, so absence
from it is not evidence of absence on disk. `near_taq` is therefore scanned from
the filesystem directly and the two sources are kept apart in the index.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import time

ARCHIVE = pathlib.Path(os.environ.get(
    "PPW_ARCHIVE",
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902"))
WRDS = ARCHIVE / "p1_refraction_wrds_shared"
RAW = WRDS / "raw"
META = WRDS / "meta"
MIGRATION_META = ARCHIVE / "_migration_meta"
MANIFEST = MIGRATION_META / "FINAL_SCC_MANIFEST.tsv"
NEAR_TAQ = RAW / "rescue_remaining" / "near_taq"

WORK = pathlib.Path(os.environ.get(
    "PPW_WORK",
    "/projectnb/econdept/qluo/news_price_discovery/prepurchase_wrds"))
OUT = WORK / "out"          # licensed data stays here, never in the repo
LOGS = WORK / "logs"
INDEX = OUT / "s7_file_index.tsv"

# The three instruments this instruction bounds the exercise to.
INSTRUMENTS = ("SPY", "XLK", "XLF")
SPY_PERMNO = 84398          # SHRCD 73: a common-stock filter would drop it
ANALYSIS_START = "2019-01-01"
ANALYSIS_END = "2023-12-31"


def load_manifest():
    """Baseline manifest as (bytes, relpath). No header; size then tab then path."""
    import pandas as pd
    m = pd.read_csv(MANIFEST, sep="\t", names=["bytes", "path"], dtype={"path": str})
    m["mib"] = m.bytes / 1024 ** 2
    m["source"] = "baseline_manifest"
    return m


def scan_near_taq():
    """Post-snapshot rescue files, read from disk because they postdate the manifest."""
    import pandas as pd
    if not NEAR_TAQ.exists():
        return pd.DataFrame(columns=["bytes", "path", "mib", "source"])
    rows = [{"bytes": p.stat().st_size,
             "path": str(p.relative_to(WRDS)),
             "source": "near_taq_scan"}
            for p in sorted(NEAR_TAQ.rglob("*")) if p.is_file()]
    d = pd.DataFrame(rows)
    if len(d):
        d["mib"] = d.bytes / 1024 ** 2
    return d


def file_index():
    """The one combined index. Built once by s7_01 and read by everything after."""
    import pandas as pd
    if INDEX.exists():
        return pd.read_csv(INDEX, sep="\t", dtype={"path": str})
    import pandas as pd
    d = pd.concat([load_manifest(), scan_near_taq()], ignore_index=True)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(INDEX, sep="\t", index=False)
    return d


def abspath(relpath):
    return WRDS / relpath


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
            if limit and fh.tell() > limit:
                break
    return h.hexdigest()


def git_rev():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=pathlib.Path(__file__).parent,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def provenance(stage, inputs, notes=None):
    """Write a lineage record beside each stage output.

    Inputs are recorded by path and size rather than by content hash for the
    large Parquet parts: hashing 10 GiB to prove which file was read costs more
    than it settles, and the archive is checksum-verified and immutable.
    """
    rec = {"stage": stage, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "git_rev": git_rev(), "archive": str(ARCHIVE),
           "inputs": [{"path": str(p),
                       "bytes": pathlib.Path(p).stat().st_size
                       if pathlib.Path(p).exists() else None} for p in inputs],
           "notes": notes or {}}
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"{stage}.lineage.json").write_text(json.dumps(rec, indent=2))
    return rec
