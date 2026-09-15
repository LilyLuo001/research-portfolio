#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

P = Path(__file__).with_name("xnys_sessions_2019_2026-08-31.csv")
d = pd.read_csv(P, dtype=str).set_index("session_date")

def opened(day, open_local, close_local, open_utc, close_utc):
    r=d.loc[day]
    assert (r.open_local,r.close_local,r.open_utc[-9:-1],r.close_utc[-9:-1]) == (open_local,close_local,open_utc,close_utc)

assert d.index.is_unique and len(d)==1926
assert set(d.calendar_timezone)=={"America/New_York"}
assert not any(pd.to_datetime(d.index).weekday>=5)
# Winter/summer UTC and DST boundary transitions.
opened("2024-03-08","09:30:00","16:00:00","14:30:00","21:00:00")
opened("2024-03-11","09:30:00","16:00:00","13:30:00","20:00:00")
opened("2024-11-01","09:30:00","16:00:00","13:30:00","20:00:00")
opened("2024-11-04","09:30:00","16:00:00","14:30:00","21:00:00")
# Historical/current official-calendar examples.
opened("2019-07-03","09:30:00","13:00:00","13:30:00","17:00:00")
opened("2020-11-27","09:30:00","13:00:00","14:30:00","18:00:00")
opened("2024-07-03","09:30:00","13:00:00","13:30:00","17:00:00")
opened("2025-11-28","09:30:00","13:00:00","14:30:00","18:00:00")
for closed in ["2019-07-04","2020-11-26","2021-12-24","2022-06-20","2024-07-04","2026-07-03"]:
    assert closed not in d.index
assert "2021-06-18" in d.index  # Juneteenth was first an XNYS holiday in 2022.
print('{"status":"PASS","fixture_assertions":18}')
