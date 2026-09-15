from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'code'))
from linkage_contract import valid_at,envelope_status,session_status
from source_side_event_envelope import normalize_cusips,filter_links_to_seed,join_events_to_seed_links
def test_inclusive_pit_interval():
 assert valid_at('2020-01-01','2021-06-11','2021-06-11')
 assert not valid_at('2021-06-12',None,'2021-06-11')
def test_ambiguity_fails_closed():
 assert envelope_status(2,True,True,True)=='AMBIGUOUS_PIT_LINK'
def test_clock_without_calendar_is_not_rth():
 assert session_status('SESSION_INPUT_READY',None,None,None)=='NOT_RUN_CALENDAR_INTERVAL_UNAVAILABLE'
def test_invalid_or_nonseed_style_identifiers_do_not_enter_cusip_envelope():
 import pandas as pd
 assert set(normalize_cusips(pd.Series(['12345678','bad','123456789',None]))) == {'12345678'}
def test_nonseed_bridge_rows_are_excluded_before_envelope_join():
 import pandas as pd
 x=pd.DataFrame({'permno':[10,99],'ncusip':['11111111','99999999']})
 assert filter_links_to_seed(x,{10}).permno.tolist()==[10]
def test_event_joins_only_matching_normalized_seed_link():
 import pandas as pd
 events=pd.DataFrame({'cusip':['11111111','22222222']})
 links=pd.DataFrame({'cusip':['11111111'],'permno':[10]})
 out=join_events_to_seed_links(events,links)
 assert out.permno.iloc[0]==10 and pd.isna(out.permno.iloc[1])
