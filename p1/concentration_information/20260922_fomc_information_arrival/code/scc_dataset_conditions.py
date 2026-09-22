#!/usr/bin/env python3
"""Query Databento source condition metadata for the fixed FOMC manifest."""
from __future__ import annotations
import argparse, json, os
from datetime import date, timedelta
from pathlib import Path
import databento as db

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",required=True,type=Path);ap.add_argument("--out",required=True,type=Path);a=ap.parse_args()
    key=os.getenv("DATABENTO_API_KEY")
    if not key:raise RuntimeError("DATABENTO_API_KEY absent")
    client=db.Historical(key);manifest=json.loads(a.manifest.read_text());rows=[]
    for dataset in sorted({x["dataset"] for x in manifest["requests"]}):
        for day in sorted({x["date"] for x in manifest["requests"] if x["dataset"]==dataset}):
            start=date.fromisoformat(day);value=client.metadata.get_dataset_condition(dataset=dataset,start_date=day,end_date=str(start+timedelta(days=1)))
            rows.append({"dataset":dataset,"date":day,"response":value})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps({"status":"COMPLETE_AUTHENTICATED_METADATA","rows":rows},indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"COMPLETE_AUTHENTICATED_METADATA","queries":len(rows)}))
if __name__=="__main__":main()
