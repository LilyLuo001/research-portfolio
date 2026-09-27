#!/usr/bin/env python3
"""Correct grouping scope wording without touching sample membership or texts."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pack", required=True)
    a = p.parse_args()
    root = Path(a.pack)
    grouping_path = root / "grouping_quality_report.json"
    grouping = json.loads(grouping_path.read_text())
    grouping.update({
        "algorithm": "one representative per observed Records.COMPANY_ID company-scrape key, exact V5-normalized SHA256, and conservative masked-token signature",
        "group_unit": "Records.COMPANY_ID is a company-scrape identifier; parent employer/subsidiary/site harmonization is unverified.",
        "algorithm_limit": "The masked signature catches some near-identical boilerplate with changed long numerals/simple addresses. It is a conservative approximation, not exhaustive near-duplicate or semantic similarity detection.",
        "residual_leakage": "Related parent/subsidiary/site entities with different company-scrape IDs and paraphrased/cross-employer templates may remain across splits."
    })
    write(grouping_path, grouping)
    manifest_path = root / "sample_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update({
        "dedup_and_split_rule": "Exclude frozen prior cases/templates/company-scrape IDs; select at most one ad per observed Records.COMPANY_ID, exact normalized template, and conservative masked-token signature. Chosen observed IDs/signatures do not cross splits. Parent/subsidiary/site harmonization and exhaustive near-duplicate detection remain unverified.",
        "near_group_algorithm": "V5 normalize; mask numerals with >=2 digits and simple street-address tokens; SHA256 exact signature; conservative approximation that may miss paraphrases and cross-entity templates",
        "methodology_metadata_correction": "Clarified the observed company-scrape grouping unit and residual leakage; sample membership and all texts unchanged.",
        "methodology_metadata_corrected_utc": dt.datetime.now(dt.timezone.utc).isoformat()
    })
    rel = "grouping_quality_report.json"
    manifest["files"][rel] = {"sha256": sha(grouping_path), "bytes": grouping_path.stat().st_size}
    write(manifest_path, manifest)
    write(root / "PACK_COMPLETE", {"status": "complete", "manifest_sha256": sha(manifest_path)})
    print(json.dumps({"status": "corrected", "manifest_sha256": sha(manifest_path)}))


if __name__ == "__main__":
    main()
