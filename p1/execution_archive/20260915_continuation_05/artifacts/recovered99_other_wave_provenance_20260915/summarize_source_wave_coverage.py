#!/usr/bin/env python3
"""Local aggregate-only reconciliation of the two permitted metadata projections."""
from pathlib import Path
import hashlib, json
import pandas as pd

HERE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def vals(s): return ';'.join(sorted(set(str(x) for x in s.dropna() if str(x))))
e=pd.read_csv(HERE/'exposure_stock_wave_metadata_projection.csv',usecols=['wave_id','effective_date'],dtype=str)
u=pd.read_csv(HERE/'public_fund_series_metadata_projection.csv',usecols=['wave_id','effective_date','pre_series_id','post_series_id'],dtype=str)
rows=[]
for wave,g in e.groupby('wave_id',sort=True):
    q=u[u.wave_id.eq(wave)]; ed={x for x in g.effective_date.dropna() if x}; ud={x for x in q.effective_date.dropna() if x}
    status='OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA' if q.empty else ('UNKNOWN_EFFECTIVE_DATE_IN_ONE_OR_BOTH_SOURCES' if not ed or not ud else ('AT_LEAST_ONE_EXACT_EFFECTIVE_DATE_MATCH' if ed&ud else 'WAVE_PRESENT_EFFECTIVE_DATE_CONFLICT_RETAINED'))
    rows.append({'exposure_wave_id':wave,'exposure_effective_dates':vals(g.effective_date),'public_universe_effective_dates':vals(q.effective_date),'public_pre_series_count':q.pre_series_id.nunique(),'public_post_series_count':q.post_series_id.nunique(),'source_wave_public_metadata_relation':status})
d=pd.DataFrame(rows); d.to_csv(HERE/'full_artifacts/source_wave_to_public_universe_coverage.csv',index=False,lineterminator='\n')
r={'status':'PASS','exposure_source_wave_count':len(d),'exact_date_match_waves':int(d.source_wave_public_metadata_relation.eq('AT_LEAST_ONE_EXACT_EFFECTIVE_DATE_MATCH').sum()),'missing_public_universe_waves':int(d.source_wave_public_metadata_relation.eq('OTHER_WAVE_MISSING_FROM_PUBLIC_UNIVERSE_METADATA').sum()),'unknown_date_waves':int(d.source_wave_public_metadata_relation.eq('UNKNOWN_EFFECTIVE_DATE_IN_ONE_OR_BOTH_SOURCES').sum()),'effective_date_conflict_waves':int(d.source_wave_public_metadata_relation.eq('WAVE_PRESENT_EFFECTIVE_DATE_CONFLICT_RETAINED').sum()),'output_sha256':sha(HERE/'full_artifacts/source_wave_to_public_universe_coverage.csv'),'code_sha256':sha(__file__),'protected_rows_read':False,'financial_or_outcome_values_read':False}
(HERE/'source_wave_coverage_receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps(r))
