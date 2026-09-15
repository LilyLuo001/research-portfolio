"""Custodian-side, outcome-blind PIT bridge for the E007 seed roster.

Reads only PERMNO/ncusip/sdate/edate/score from the archived CRSP--IBES link.
It preserves every date-valid link; it does not select or threshold score.
"""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

EXPECTED_SEED="0c5d9175d53e76d746777776c2ff3ee46cc038f7227120eb22e86077a6d05555"
COLS=["permno","ncusip","sdate","edate","score"]
def sha(p):
 h=hashlib.sha256();
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=Path,required=True);ap.add_argument('--bridge',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args()
 if sha(a.seed)!=EXPECTED_SEED: raise ValueError('seed hash mismatch')
 a.out_dir.mkdir(parents=True,exist_ok=False)
 seed=pd.read_csv(a.seed,usecols=['permno','wave_id','effective_date','source_row_locator'],dtype={'permno':'Int64','wave_id':'string','effective_date':'string','source_row_locator':'string'})
 import pyarrow.parquet as pq
 permnos=sorted(int(x) for x in seed.permno.dropna().unique())
 link=pq.read_table(a.bridge,columns=COLS,filters=[('permno','in',permnos)]).to_pandas()
 link['permno']=pd.to_numeric(link['permno'],errors='coerce').astype('Int64');link['sdate']=pd.to_datetime(link['sdate'],errors='coerce');link['edate']=pd.to_datetime(link['edate'],errors='coerce')
 x=seed.merge(link,on='permno',how='left',validate='many_to_many');eff=pd.to_datetime(x.effective_date,errors='coerce')
 valid=x.sdate.notna() & (x.sdate<=eff) & (x.edate.isna() | (eff<=x.edate))
 mapped=x.loc[valid].copy(); mapped['ncusip']=mapped.ncusip.astype('string').str.strip()
 usable=mapped.loc[mapped.ncusip.str.fullmatch(r'[A-Za-z0-9]{8}',na=False)].copy()
 keys=['permno','wave_id','effective_date']
 counts=usable.groupby(keys).size().rename('date_valid_mapping_count').reset_index()
 invalid=mapped.loc[~mapped.ncusip.str.fullmatch(r'[A-Za-z0-9]{8}',na=False)].groupby(keys).size().rename('invalid_identifier_count').reset_index()
 base=seed.merge(counts,on=keys,how='left').merge(invalid,on=keys,how='left');base['date_valid_mapping_count']=base.date_valid_mapping_count.fillna(0).astype(int);base['invalid_identifier_count']=base.invalid_identifier_count.fillna(0).astype(int)
 base['mapping_status']=base.apply(lambda r:'UNIQUE' if r.date_valid_mapping_count==1 else ('AMBIGUOUS_MULTIPLE' if r.date_valid_mapping_count>1 else ('INVALID_IDENTIFIER' if r.invalid_identifier_count>0 else 'MISSING')),axis=1)
 usable.to_csv(a.out_dir/'date_valid_pit_mappings.csv',index=False)
 base.to_csv(a.out_dir/'seed_mapping_status.csv',index=False)
 cusips=sorted(usable.ncusip.unique());pd.DataFrame({'cusip':cusips}).to_csv(a.out_dir/'candidate_cusips.csv',index=False)
 receipt={'seed_sha256':sha(a.seed),'bridge_sha256':sha(a.bridge),'seed_rows':len(seed),'bridge_rows_read_after_permno_filter':len(link),'date_valid_usable_mapping_rows':len(usable),'mapped_seed_rows':int((base.date_valid_mapping_count>0).sum()),'ambiguous_seed_rows':int((base.date_valid_mapping_count>1).sum()),'invalid_identifier_seed_rows':int((base.mapping_status=='INVALID_IDENTIFIER').sum()),'missing_seed_rows':int((base.mapping_status=='MISSING').sum()),'candidate_cusips':len(cusips),'candidate_cusips_sha256':sha(a.out_dir/'candidate_cusips.csv'),'score_rule':'NONE_ALL_DATE_VALID_USABLE_LINKS_RETAINED','columns_projected':COLS,'outcome_fields_read':False}
 (a.out_dir/'pit_bridge_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
