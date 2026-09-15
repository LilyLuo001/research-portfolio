"""Narrow metadata projection. Row-level licensed outputs remain on SCC."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914')
RAW=ROOT.parent/'WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw'
OUT=ROOT/'gate1_followup_20260915'
EVENTS=ROOT/'union_v2_earnings_inputs/selected_event_metadata.csv'
NAMES=RAW/'crsp_dsenames_full.parquet'
ACTUAL=ROOT/'union_v2_earnings_inputs/licensed_actuals_selected.parquet'
E=['association_id','permno','pends','announcement_date','announcement_times_all','date_valid_raw_symbol','date_valid_ncusip','sample_period','wave_id']
N=['permno','namedt','nameendt','ticker','ncusip','shrcls','tsymbol']
T=['permno','cusip','pends','pdicity','anndats','anntims','actdats','acttims']

def main():
    OUT.mkdir(exist_ok=True)
    e=pd.read_csv(EVENTS,usecols=E,dtype={'date_valid_ncusip':str})
    assert len(e)==852 and e.association_id.is_unique
    e['event_dt']=pd.to_datetime(e.announcement_date)
    e['pends_dt']=pd.to_datetime(e.pends)
    n=pq.read_table(NAMES,columns=N,filters=[('permno','in',sorted(e.permno.unique()))]).to_pandas()
    n['namedt']=pd.to_datetime(n.namedt);n['nameendt']=pd.to_datetime(n.nameendt)
    j=e.merge(n,on='permno',how='left')
    j=j[(j.namedt<=j.event_dt)&(j.event_dt<=j.nameendt)].copy()
    counts=j.groupby('association_id').size()
    j.to_csv(OUT/'licensed_identity_intervals.csv',index=False)
    target=j[j.permno==27618]
    identity=dict(event_rows=len(e),matching_name_interval_rows=len(j),associations_matched=int(e.association_id.isin(j.association_id).sum()),associations_with_multiple_intervals=int((counts>1).sum()),ncusip_agreement=int((j.ncusip.astype(str)==j.date_valid_ncusip).sum()),base_ticker_agreement=int((j.ticker==j.date_valid_raw_symbol).sum()),crd_associations=len(target),crd_class_counts=target.shrcls.fillna('NULL').value_counts().to_dict(),crd_cusip_agreement=int((target.ncusip.astype(str)==target.date_valid_ncusip).sum()),class_identity='HISTORICAL_CRSP_CLASS_B' if len(target)==12 and target.shrcls.eq('B').all() else 'UNRESOLVED')
    a=pq.read_table(ACTUAL,columns=T).to_pandas()
    for c in ['pends','anndats','actdats']:a[c]=pd.to_datetime(a[c])
    a=a.merge(e[['association_id','permno','pends_dt','event_dt','announcement_times_all']],left_on=['permno','pends'],right_on=['permno','pends_dt'],how='inner')
    a['date_agreement']=a.anndats.eq(a.event_dt)
    a['time_agreement']=a.anntims.astype(str).eq(a.announcement_times_all.astype(str))
    a['announcement_seconds_nonzero']=a.anntims.astype(str).str.extract(r':(\d{2})$')[0].fillna('UNKNOWN').ne('00')
    a['midnight_sentinel']=a.anntims.astype(str).eq('00:00:00')
    a['activation_minus_announcement_days']=(a.actdats-a.anndats).dt.days
    a.to_csv(OUT/'licensed_clock_metadata_audit.csv',index=False)
    quality=dict(projected_source_rows=len(a),unique_associations=a.association_id.nunique(),pdicity_counts=a.pdicity.astype(str).value_counts().to_dict(),date_agreement=int(a.date_agreement.sum()),time_agreement=int(a.time_agreement.sum()),announcement_seconds_nonzero=int(a.announcement_seconds_nonzero.sum()),midnight_sentinel=int(a.midnight_sentinel.sum()),activation_date_before_announcement=int((a.activation_minus_announcement_days<0).sum()),activation_date_same=int((a.activation_minus_announcement_days==0).sum()),activation_date_later=int((a.activation_minus_announcement_days>0).sum()),timezone='UNVERIFIED',public_release_precision='UNVERIFIED_NOT_INFERRED_FROM_FORMAT',session='NOT_CLASSIFIED')
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),identity=identity,clock_metadata=quality,approved_columns={'events':E,'names':N,'actuals_metadata_projection':T},raw_values_projected=False,row_level_outputs='SCC_ONLY',source_files=[str(EVENTS),str(NAMES),str(ACTUAL)],event_manifest_sha256=hashlib.sha256(EVENTS.read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'identity_clock_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
