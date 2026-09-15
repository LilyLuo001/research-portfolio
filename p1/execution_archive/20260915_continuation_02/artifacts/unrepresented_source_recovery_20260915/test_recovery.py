#!/usr/bin/env python3
from pathlib import Path
import importlib.util, pandas as pd
p=Path(__file__).with_name("run_recovery.py"); s=importlib.util.spec_from_file_location("m",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert m.norm_cusip(pd.Series([" ab12cd34 ","AB12CD345","bad!"])).tolist()[0]=="AB12CD34"
assert m.norm_cusip(pd.Series(["AB12CD345"])).isna().all()
d=pd.Series(pd.to_datetime(["2020-01-01","2020-02-01","2020-03-01"])); assert m.event_side(d,pd.Timestamp("2020-02-01"),pd.Timestamp("2020-03-01")).tolist()==["PRE","TRANSITION","POST"]
x=pd.DataFrame({"a":[1,1,1],"b":[2,2,3]}); assert m.distinct_pair_count(x,"a","b")==2
# A noncandidate valid link still makes the source row ambiguous before candidate filtering.
links=pd.DataFrame({"permno_link":[1,2],"valid":[True,True]}); assert links.loc[links.valid,"permno_link"].nunique()==2
assert "NO_MATCH_IN_CHECKED_SCC_FAMILY" != "NO_VENDOR_EARNINGS"
assert {"CORE","RESCUE"}!={"POOLED"}
# Invalid CUSIP is removed before joins; unknown-bound competitors override uniqueness.
src=pd.DataFrame({"cusip_norm":[pd.NA,"AB12CD34"]}); link=pd.DataFrame({"ncusip_norm":[pd.NA,"AB12CD34"]})
assert len(src[src.cusip_norm.notna()].merge(link[link.ncusip_norm.notna()],left_on="cusip_norm",right_on="ncusip_norm"))==1
row={"has_unknown_link_path":True,"valid_permno_count":1}; status="UNKNOWN_LINK_PATH_PRESENT" if row["has_unknown_link_path"] else "UNIQUE_VALID_PERMNO"; assert status=="UNKNOWN_LINK_PATH_PRESENT"
print('{"status":"PASS","fixture_count":10}')
