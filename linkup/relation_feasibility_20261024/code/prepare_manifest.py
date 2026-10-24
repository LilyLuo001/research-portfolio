#!/usr/bin/env python3
"""SCNet scheduler-only enumerate exact bounded original validation paths.

No search of advertisements or semantic classification. Keeps missing originals
visible in the inventory rather than selecting other reviews with similar IDs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-root", required=True)
    p.add_argument("--formal-reviews", required=True)
    p.add_argument("--freeze", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("must run in actual SCNet Slurm job")
    base = Path(a.private_root)
    paths = [Path(a.formal_reviews), base / "batch001/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl"]
    paths += [base / ("batch002_004/batch%03d/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl" % n) for n in range(2, 5)]
    paths += [base / ("continuation/prepared/batch%03d/validated/VALIDATED_REVIEWS_ALL100_PRIVATE.jsonl" % n) for n in range(5, 70)]
    freeze = Path(a.freeze)
    value = {"freeze": {"path": str(freeze), "sha256": digest(freeze)},
             "sources": [{"path": str(x), "sha256": digest(x)} for x in paths if x.is_file()],
             "missing_expected_sources": [str(x) for x in paths if not x.is_file()],
             "packets": [], "use_frozen_frame_contexts": True}
    with open(a.output, "x", encoding="utf-8") as f:
        os.chmod(a.output, 0o600)
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
