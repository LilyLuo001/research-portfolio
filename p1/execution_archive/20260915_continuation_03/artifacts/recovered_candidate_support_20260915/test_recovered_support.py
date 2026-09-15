#!/usr/bin/env python3
from datetime import time
import pandas as pd
from run_recovered_support import parse_clock, nominal_clock, analyst_count

assert parse_clock("09:30:00") == time(9,30)
assert parse_clock("15:00:00") == time(15,0)
assert parse_clock("not-a-time") is None
assert nominal_clock("09:29:59") is False
assert nominal_clock("09:30:00") is True
assert nominal_clock("15:00:00") is True
assert nominal_clock("15:00:01") is False
d=pd.DataFrame({"anndats":pd.to_datetime(["2020-01-02","2020-03-31","2020-04-01"]),"analys":["A","B","C"]})
assert analyst_count(d,pd.Timestamp("2020-04-01"),90)==2
assert analyst_count(pd.DataFrame({"anndats":pd.to_datetime([]),"analys":pd.Series([],dtype="string")}),pd.Timestamp("2020-04-01"),90)==0
print('{"status":"PASS","fixture_count":9}')
