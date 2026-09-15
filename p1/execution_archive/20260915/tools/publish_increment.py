#!/usr/bin/env python3
"""Publish a named increment without changing the prior committed snapshot."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import publish_artifacts as policy

CALENDAR_FIELDS = {
    "calendar_id", "session_date", "calendar_timezone", "open_local", "close_local",
    "open_utc", "close_utc", "session_open_utc", "session_close_utc", "source_version",
    "calendar_version", "is_early_close", "session_minutes", "library_version",
    "session_type", "library_name", "tzdata_version",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--stage", action="append", required=True)
    args = parser.parse_args()
    if "/" in args.name or args.name in {".", ".."}: raise ValueError("invalid increment")
    base = policy.BASE.parent / args.name
    if base.exists(): raise FileExistsError("Preserve existing increment; use a new name")
    source_root = policy.SOURCES["pilot_workspace"]
    entries = []
    for stage in args.stage:
        if "/" in stage or stage in {".", ".."}: raise ValueError("invalid stage")
        root = source_root / stage
        if not root.is_dir(): raise FileNotFoundError(stage)
        for path in sorted(root.rglob("*")):
            if not path.is_file(): continue
            rel = path.relative_to(source_root)
            reason = policy.precheck(rel, path)
            # New calendar is generated exchange metadata, not research-row data.
            calendar = stage.startswith("exchange_calendar_") and path.suffix == ".csv"
            if calendar: reason = None
            if stage == "unrepresented_source_recovery_20260915" and path.name in {
                "recovery_by_wave_tier_family.csv", "support_by_wave_tier_family_side.csv",
                "candidate_source_overlap_aggregate.csv", "source_family_record_overlap.csv",
                "source_partition_counts.csv",
            }: reason = None
            entry = {"source_path": str(path), "relative_path": str(rel), "size_bytes": path.stat().st_size}
            if reason:
                entries.append({**entry, "status": "EXCLUDED", "reason": reason}); continue
            raw = path.read_bytes(); content = raw.decode("utf-8")
            if policy.secret_hit(content): raise ValueError(f"Possible secret; publication stopped: {rel}")
            if path.suffix == ".json" and policy.json_row_risk(json.loads(content)):
                entries.append({**entry, "status": "EXCLUDED", "reason": "POSSIBLE_ROW_LEVEL_JSON"}); continue
            if path.suffix == ".csv":
                fields = set(next(csv.reader(io.StringIO(content))))
                if calendar and not fields <= CALENDAR_FIELDS: raise ValueError(f"Unapproved calendar fields: {sorted(fields-CALENDAR_FIELDS)}")
                if {x.lower() for x in fields} & (policy.IDENTITY_KEYS | policy.VALUE_KEYS): raise ValueError("Row-level/value CSV rejected")
            target = base / "artifacts" / rel
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            entries.append({**entry, "status": "PUBLISHED", "repository_path": str(target.relative_to(policy.REPO)), "sha256": hashlib.sha256(raw).hexdigest()})
    base.mkdir(parents=True, exist_ok=True)
    index = {"stages": args.stage, "files": entries, "prior_snapshot_unchanged": True, "raw_inputs_modified": False}
    (base / "ARTIFACT_INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({"increment": args.name, "published": sum(e["status"] == "PUBLISHED" for e in entries), "excluded": sum(e["status"] == "EXCLUDED" for e in entries)}))

if __name__ == "__main__": main()
