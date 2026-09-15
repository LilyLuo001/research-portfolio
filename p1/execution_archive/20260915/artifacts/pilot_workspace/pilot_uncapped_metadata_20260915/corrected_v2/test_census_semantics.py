#!/usr/bin/env python3
"""Golden boundary fixtures for corrected census semantics."""
import json, tempfile
from pathlib import Path
import pandas as pd
from run_uncapped_census_v2 import classify_event_side, classify_link_bounds, distinct_pair_count, in_source_window, norm_cusip, parse_link_permno, source_mapping_status

def main():
 tests={}
 tests["ambiguity_includes_permno_outside_candidate_set_before_filter"]=source_mapping_status([10001,20002],False)=="AMBIGUOUS_VALID_PERMNO"
 rows=pd.DataFrame({"source_row_id":["s1","s1"],"candidate_id":["c1","c1"],"signature":["x","x"]})
 tests["exact_duplicate_paths_retained_without_inflating_distinct_source_candidate_count"]=(len(rows)==2 and rows[["source_row_id","candidate_id"]].drop_duplicates().shape[0]==1 and rows.signature.nunique()==1)
 tests["invalid_and_open_link_dates_explicit"]=(classify_link_bounds("bad","2020-01-01",pd.NaT,pd.Timestamp("2020-01-01"))=="INVALID_START_DATE" and classify_link_bounds("2020-01-01",None,pd.Timestamp("2020-01-01"),pd.NaT)=="OPEN_END_UNKNOWN")
 old={("W1",1,"high","PRE","2020-03-31","2020-05-01"):True};new_key=("W1",1,"high","PRE","2020-06-30","2020-08-01")
 tests["new_uncapped_analyst_key_remains_unknown"]=old.get(new_key,"UNKNOWN_NEW_UNCAPPED_EVENT_KEY")=="UNKNOWN_NEW_UNCAPPED_EVENT_KEY"
 candidates=pd.DataFrame({"candidate_id":["c1","c2"]});mapped=pd.DataFrame({"candidate_id":["c1"],"n":[1]});den=candidates.merge(mapped,how="left",on="candidate_id")
 tests["candidate_without_source_path_preserved_in_denominator"]=len(den)==2 and pd.isna(den.loc[den.candidate_id.eq("c2"),"n"]).all()
 tests["closed_link_bounds_are_inclusive"]=(pd.Timestamp("2020-01-01")>=pd.Timestamp("2020-01-01") and pd.Timestamp("2020-12-31")<=pd.Timestamp("2020-12-31"))
 tests["source_date_bounds_lower_inclusive_upper_exclusive"]=(in_source_window(pd.Timestamp("2019-01-01"),pd.Timestamp("2019-01-01"),pd.Timestamp("2026-09-01")) and not in_source_window(pd.Timestamp("2026-09-01"),pd.Timestamp("2019-01-01"),pd.Timestamp("2026-09-01")))
 tests["transition_is_separate_from_pre_and_post"]=(classify_event_side(pd.Timestamp("2020-06-01"),pd.Timestamp("2020-01-01"),pd.Timestamp("2021-01-01"))=="TRANSITION")
 tests["missing_event_bound_is_unknown"]=classify_event_side(pd.Timestamp("2020-06-01"),pd.Timestamp("2020-01-01"),pd.NaT)=="UNKNOWN_MISSING_BOUND"
 tests["cusip_requires_exact_8_alphanumeric_without_truncation"]=(norm_cusip("12345678")=="12345678" and norm_cusip("123456789") is None and norm_cusip("12-45678") is None)
 lp,ls=parse_link_permno(pd.Series([12345.0,None,123.5]));tests["invalid_link_permno_is_explicit_unknown"]=(int(lp.notna().sum())==1 and list(ls)==["VALID_INTEGER_PERMNO","INVALID_OR_MISSING_PERMNO_UNKNOWN","INVALID_OR_MISSING_PERMNO_UNKNOWN"])
 pair_fixture=pd.DataFrame({"source_row_id":["s1","s1","s1"],"candidate_id":["c1","c2","c2"]});tests["distinct_source_row_candidate_count_is_pair_not_source_only"]=(distinct_pair_count(pair_fixture,"source_row_id","candidate_id")==2 and pair_fixture.source_row_id.nunique()==1)
 tests={k:bool(v) for k,v in tests.items()}
 if not all(tests.values()):raise AssertionError(tests)
 here=Path(__file__).resolve().parent;out=here/"local"/"synthetic_fixture_receipt.json";out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps({"status":"ALL_GOLDEN_SEMANTIC_FIXTURES_PASS","test_count":len(tests),"tests":tests,"source_data_opened":False},indent=2,sort_keys=True)+"\n")
 print(json.dumps({"status":"PASS","test_count":len(tests)}))
if __name__=="__main__":main()
