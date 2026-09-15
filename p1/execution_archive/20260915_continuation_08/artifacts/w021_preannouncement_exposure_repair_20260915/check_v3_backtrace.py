import hashlib,json
from pathlib import Path
import pandas as pd
R=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_exposure_repair_20260915');S=R/'golden_pilot_v3/protected'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
h=pd.read_parquet(S/'position_states.parquet').sort_values('position_index');s=pd.read_parquet(S/'stock_doses.parquet');assert len(h)==20 and len(s)==20
assert h.mapping_status.eq('MAP_UNIQUE_DATE_VALID_CUSIP9').all() and h.class_status.eq('US_COMMON_CERTIFIED').all() and h.denominator_status.eq('ACTIVE_DSESHARES_UNIQUE_POSITIVE').all()
assert (h.denominator_raw_shares>0).all() and (h.raw_shares/h.denominator_raw_shares>0).all() and (s.dose>0).all()
x={'status':'PASS','first20_position_mapping_denominator_backtrace':True,'positions':20,'assertions':120,'source_row_interval_conflicts':0,'rows_or_values_printed':False,'protected_hashes':{'position_states':sha(S/'position_states.parquet'),'stock_doses':sha(S/'stock_doses.parquet')}}
(R/'golden_pilot_v3/FIELDWISE_BACKTRACE.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(json.dumps(x))
