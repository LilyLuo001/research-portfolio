"""SCC-only nominal source-clock classification against a public 2023 calendar.

No source clock corrections, no next-open substitution, no outcome values.
"""
import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd


def classify(day, stamp, cal):
    if day.weekday() >= 5:
        return "WEEKEND_CLOSED"
    if day.isoformat() in cal["closed_dates"]:
        return "HOLIDAY_CLOSED"
    if stamp is None:
        return "UNKNOWN_TIME"
    op=time.fromisoformat(cal["core_open"])
    close=time.fromisoformat(cal["core_close_early"] if day.isoformat() in cal["early_close_dates"] else cal["core_close_normal"])
    return "PRE_OPEN" if stamp<op else "RTH" if stamp<close else "AFTER_CLOSE"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--calendar", required=True)
    p.add_argument("--out", required=True)
    a=p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    cal=json.loads(Path(a.calendar).read_text()); zone=ZoneInfo(cal["timezone"])
    assert classify(date(2023,7,3),time(13,1),cal)=="AFTER_CLOSE"
    assert classify(date(2023,7,4),time(10),cal)=="HOLIDAY_CLOSED"
    assert classify(date(2023,7,8),time(8),cal)=="WEEKEND_CLOSED"
    assert classify(date(2023,7,5),time(9,30),cal)=="RTH"
    assert datetime(2023,1,3,12,tzinfo=zone).utcoffset()==timedelta(hours=-5)
    assert datetime(2023,7,5,12,tzinfo=zone).utcoffset()==timedelta(hours=-4)
    rows=pd.read_parquet(a.input,columns=["issuer_rank","permco","anndats","anntims"])
    assert len(rows)==len(rows.drop_duplicates())
    result=[]
    for r in rows.itertuples(index=False):
        day=pd.Timestamp(r.anndats).date()
        if day.year!=cal["year"]:
            raise ValueError("Calendar year mismatch")
        try:
            stamp=time.fromisoformat(str(r.anntims).strip())
        except (ValueError,TypeError):
            stamp=None
        old="UNKNOWN_TIME" if stamp is None else "PRE_OPEN_COARSE" if stamp<time(9,30) else "RTH_COARSE" if stamp<time(16) else "AFTER_CLOSE_COARSE"
        local=datetime.combine(day,stamp,tzinfo=zone) if stamp else None
        result.append({"issuer_rank":r.issuer_rank,"permco":r.permco,"source_date":day.isoformat(),
            "source_time":str(r.anntims),"old_coarse_class":old,"calendar_class":classify(day,stamp,cal),
            "nominal_utc":local.astimezone(ZoneInfo("UTC")).isoformat() if local else None,
            "earliest_public_time":"UNKNOWN", "accuracy_bound":"UNKNOWN"})
    df=pd.DataFrame(result)
    df.to_parquet(out/"private_calendar_classification.parquet",index=False)
    summary={"input_groups":len(df),"session_counts":dict(Counter(df.calendar_class)),
        "transition_counts":[{"old":k[0],"new":k[1],"n":v} for k,v in Counter(zip(df.old_coarse_class,df.calendar_class)).items()],
        "source_clock_precision_pass":False,"source_clock_shift_applied":False,
        "next_open_substitution":False,"calendar_source":cal["source"],
        "calendar_sha256":hashlib.sha256(Path(a.calendar).read_bytes()).hexdigest(),
        "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_path":a.input,"input_sha256":hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),
        "closed_event_handling":"Retain in population; exclude from same-time equity-quote pilot, not relabeled next open",
        "tests":"PASS: weekend, holiday, early close, open boundary, winter/summer UTC offsets",
        "raw_outcome_values_read":False,"row_level_output":str(out/"private_calendar_classification.parquet")}
    (out/"CALENDAR_SUMMARY.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
