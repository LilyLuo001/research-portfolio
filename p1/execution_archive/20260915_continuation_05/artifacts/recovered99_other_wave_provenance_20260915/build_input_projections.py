#!/usr/bin/env python3
"""Create metadata-only projections from two pinned local exposure sources."""
from pathlib import Path
import hashlib, json
import pandas as pd

OUT=Path(__file__).resolve().parent
EXPOSURE=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv')
UNIVERSE=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_universe_gate0_pass.csv')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

e=pd.read_csv(EXPOSURE,usecols=['permno','wave_id','effective_date'],dtype=str)
e['permno']=pd.to_numeric(e.permno,errors='raise').astype(int)
e=e.drop_duplicates(['permno','wave_id','effective_date']).sort_values(['permno','wave_id','effective_date'])
e.to_csv(OUT/'exposure_stock_wave_metadata_projection.csv',index=False,lineterminator='\n')
u=pd.read_csv(UNIVERSE,usecols=['wave_id','effective_date','adviser','pre_series_id','pre_series_name','post_series_id','post_series_name','gate0'],dtype=str)
u=u.drop_duplicates().sort_values(['wave_id','pre_series_id','post_series_id'])
u.to_csv(OUT/'public_fund_series_metadata_projection.csv',index=False,lineterminator='\n')
r={'status':'METADATA_PROJECTIONS_COMPLETE','allowed_exposure_columns':['permno','wave_id','effective_date'],'allowed_universe_columns':['wave_id','effective_date','adviser','pre_series_id','pre_series_name','post_series_id','post_series_name','gate0'],'source_hashes':{str(EXPOSURE):sha(EXPOSURE),str(UNIVERSE):sha(UNIVERSE)},'projection_hashes':{'exposure_stock_wave_metadata_projection.csv':sha(OUT/'exposure_stock_wave_metadata_projection.csv'),'public_fund_series_metadata_projection.csv':sha(OUT/'public_fund_series_metadata_projection.csv')},'exposure_rows':len(e),'exposure_wave_count':e.wave_id.nunique(),'exposure_wave_ids':sorted(e.wave_id.unique()),'public_universe_rows':len(u),'public_universe_wave_count':u.wave_id.nunique(),'financial_or_outcome_values_read':False}
(OUT/'projection_receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:r[k] for k in ['status','exposure_rows','exposure_wave_count','public_universe_rows','public_universe_wave_count']}))
