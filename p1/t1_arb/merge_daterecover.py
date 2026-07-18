#!/usr/bin/env python3
"""BOX-ONLY. Fold deepseek's recovered effective_dates back and re-assemble.

Reads ops/l1/out/P1-T1-daterecover.json (from run_mopup.py), maps each
recovered ISO date onto EVERY filing accession of that conversion (so assemble's
overlay promotes it), writes p1/t1_arb/recovered_dates.json, then re-runs
assemble.py. Reports how many of the 109 held-back conversions got promoted.

Run (after run_mopup.py P1-T1-daterecover --live reports DONE):
    python p1/t1_arb/merge_daterecover.py
    python ops/runner/contracts.py events_merged p1/events_merged.csv   # expect PASS
    git add -f ops/l1/out/P1-T1-daterecover.json
    git add p1/t1_arb/recovered_dates.json p1/events_merged.csv p1/t1_arb/arb_report.md
    git commit -m "P1-T1: recover held-back effective dates, re-assemble" && git push
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t1_arb"
OUTJSON = ROOT / "ops" / "l1" / "out" / "P1-T1-daterecover.json"
SPEC = ROOT / "ops" / "l1" / "P1-T1-daterecover.yaml"
RECOVERED = HERE / "recovered_dates.json"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v if isinstance(v, dict) else None


def main():
    if not OUTJSON.exists():
        sys.exit(f"missing {OUTJSON} — run run_mopup.py P1-T1-daterecover --live first")
    out = json.loads(OUTJSON.read_text())
    import yaml
    spec = yaml.safe_load(SPEC.read_text())
    acc_map = {str(it["id"]): it.get("_accessions", [it["id"]]) for it in spec["items"]}

    recovered, got, skipped = {}, 0, []
    for rid, v in out.items():
        if rid in ("S1", "S2", "S3"):
            continue
        obj = parse(v)
        eff = str((obj or {}).get("effective_date", "NA"))
        if obj and ISO.match(eff):
            got += 1
            for acc in acc_map.get(rid, [rid]):
                recovered[acc] = {"effective_date": eff,
                                  "date_basis": obj.get("date_basis", "NA"),
                                  "evidence": obj.get("evidence", ""),
                                  "source": "full-text date-recovery (deepseek)"}
        else:
            skipped.append(rid)

    RECOVERED.write_text(json.dumps(
        {"_meta": {"recovered_conversions": got, "still_undated": len(skipped),
                   "note": "keyed by source_accession; consumed by assemble.py overlay"},
         "recovered": recovered}, indent=1))
    print(f"recovered dates for {got} conversions ({len(recovered)} filing keys); "
          f"{len(skipped)} still undated (stay needs_fulltext).")
    subprocess.run([sys.executable, str(HERE / "assemble.py")], check=True)


if __name__ == "__main__":
    main()
