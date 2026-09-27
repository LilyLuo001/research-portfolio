#!/usr/bin/env python3
"""Freeze the development/prior-pack exclusions needed by the remote finalizer."""
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    root = Path(a.root)
    dev_path = root / "stage_c_v5/development_exclusions_v5.json"
    old_path = root / "stage_c_v3/validation_pack/validation_sample.parquet"
    dev = json.loads(dev_path.read_text())
    old = pq.read_table(old_path).to_pylist()
    bundle = {
        "development_exclusions_source": str(dev_path),
        "prior_120_source": str(old_path),
        "job_hashes": sorted(set(dev["all_recorded_development_JOB_HASH"]) | {str(r["JOB_HASH"]) for r in old}),
        "normalized_text_sha256": sorted(set(dev["all_recorded_development_normalized_sha256"]) |
                                          {str(r["NORMALIZED_TEMPLATE_SHA256"]) for r in old}),
        "employer_ids": sorted(set(map(str, dev["all_recorded_development_employer_ids"])) |
                               {str(r["RECORD_COMPANY_ID"]) for r in old if r["RECORD_COMPANY_ID"] is not None}),
        "development_job_hash_count": len(dev["all_recorded_development_JOB_HASH"]),
        "prior_pack_row_count": len(old),
        "rule": "Exclude union of 72 recorded development cases/templates/employers and the entire prior 120 pack including its employers.",
    }
    text = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    Path(a.out).write_text(text)
    print(json.dumps({"job_hashes": len(bundle["job_hashes"]), "templates": len(bundle["normalized_text_sha256"]),
                      "employers": len(bundle["employer_ids"]), "sha256": hashlib.sha256(text.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
