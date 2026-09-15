#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
SRC=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/nport_crsp_security_crosswalk.csv')
OUT=Path(__file__).resolve().parent/'protected_relevant_wave_permno_series.csv'
d=pd.read_csv(SRC,usecols=['wave_id','event_id','pre_series_id','mapping_status','permno'],dtype=str)
d=d[d.wave_id.isin(['W002','W006','W016','W032']) & d.mapping_status.eq('exact_matched') & d.permno.notna()].copy()
d['permno']=pd.to_numeric(d.permno,errors='raise').astype(int)
d=d[['permno','wave_id','event_id','pre_series_id']].drop_duplicates().sort_values(['wave_id','permno','pre_series_id'])
assert set(d.wave_id)=={'W002','W006','W016','W032'}
d.to_csv(OUT,index=False)
print(len(d))
