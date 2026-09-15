#!/usr/bin/env python3
"""W021 metadata v2: ambiguity before candidate filter and hash-gated full census."""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def c8(x):
 z=str(x).strip().upper()if pd.notna(x)else ''
 return z if len(z)==8 and z.isalnum()else None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['pilot','full'],required=True);ap.add_argument('--config',required=True);ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);ap.add_argument('--pilot');a=ap.parse_args();cfg=json.load(open(a.config));inp=Path(a.inputs);out=Path(a.out);man=json.load(open(inp/'manifest.json'));fn='pilot20.csv'if a.mode=='pilot'else'candidates_39.csv';cand=pd.read_csv(inp/fn);expected=20 if a.mode=='pilot'else 39
 if sha(inp/'candidates_39.csv')!=man['input_files']['candidates_39.csv'] or sha(inp/'pilot20.csv')!=man['input_files']['pilot20.csv']:raise ValueError('input file hash mismatch')
 bind={'code_sha256':sha(__file__),'config_sha256':sha(a.config),'input_manifest_sha256':sha(inp/'manifest.json'),'candidate_roster_sha256':man['candidate_roster_sha256'],'candidates39_sha256':sha(inp/'candidates_39.csv'),'pilot20_selection_sha256':sha(inp/'pilot20.csv'),'metadata_sha256':sha(cfg['announcement_metadata']),'link_sha256':sha(cfg['historical_crsp_ibes_link'])}
 if len(cand)!=expected:raise ValueError('denominator')
 if a.mode=='full':
  r=json.load(open(a.pilot)); 
  if r.get('status')!='W021_METADATA_V2_PILOT_COMPLETE'or r.get('bindings')!=bind or not r.get('lineage_pass'):raise ValueError('FULL_BLOCKED_HASH_LINEAGE_GATE')
 if out.exists():raise FileExistsError(out)
 l=pd.read_parquet(cfg['historical_crsp_ibes_link'],columns=['permno','ncusip','sdate','edate','score']);l['cusip8']=l.ncusip.map(c8);l['perm']=pd.to_numeric(l.permno,errors='coerce');l['s']=pd.to_datetime(l.sdate,errors='coerce');l['e']=pd.to_datetime(l.edate,errors='coerce');l=l[l.cusip8.notna()]
 bs=[]
 for z in pd.read_csv(cfg['announcement_metadata'],usecols=['ticker','cusip','pends','pdicity','anndats','anntims','actdats','acttims','source_partition'],dtype=str,chunksize=200000):
  z=z[z.pdicity.eq('QTR')].copy();z['d']=pd.to_datetime(z.anndats,errors='coerce');z['cusip8']=z.cusip.map(c8);bs.append(z[z.d.notna()&z.cusip8.notna()])
 m=pd.concat(bs,ignore_index=True);m['source_row_id']=['META:'+str(i+2)for i in m.index];p=m.merge(l,on='cusip8',how='left');p['closed']=p.s.notna()&p.e.notna()&(p.s<=p.e)&(p.d>=p.s)&(p.d<=p.e)
 # The valid-permno set is assessed for every source row before it sees the frozen candidate roster.
 g=p[p.closed&p.perm.notna()].groupby('source_row_id').perm.agg(lambda x:sorted(set(x.astype(int))));p['valid_permnos']=p.source_row_id.map(g);p['mapping_status']=p.valid_permnos.map(lambda x:'UNIQUE_VALID_PERMNO'if isinstance(x,list)and len(x)==1 else('AMBIGUOUS_VALID_PERMNO'if isinstance(x,list)else'NO_VALID_PERMNO'))
 p=p[p.mapping_status.eq('UNIQUE_VALID_PERMNO')].copy();p['permno']=p.valid_permnos.str[0].astype(int);p=p.merge(cand,on='permno',how='inner');A=pd.Timestamp('2022-12-15');I=pd.Timestamp('2023-07-28');p['event_side']=p.d.map(lambda d:'PRE'if d<A else('UNKNOWN_A_DATE_BOUNDARY'if d==A else('TRANSITION'if d<I else('UNKNOWN_I_DATE_BOUNDARY'if d==I else'POST'))));p['accounting_period_date_key']=p.permno.astype(str)+':'+p.pends+':'+p.anndats;p['public_release_key']=p.accounting_period_date_key+':'+p.anntims.fillna('UNKNOWN')
 out.mkdir(parents=True);p[['source_row_id','candidate_id','permno','provisional_tier','pends','anndats','anntims','event_side','mapping_status','accounting_period_date_key','public_release_key']].to_csv(out/'protected_metadata_v2.csv',index=False);p.groupby(['provisional_tier','event_side','mapping_status']).agg(paths=('source_row_id','size'),accounting_period_date_keys=('accounting_period_date_key','nunique'),public_release_keys=('public_release_key','nunique')).reset_index().to_csv(out/'metadata_v2_aggregate.csv',index=False)
 rec={'status':'W021_METADATA_V2_PILOT_COMPLETE'if a.mode=='pilot'else'W021_METADATA_V2_FULL39_COMPLETE','candidate_denominator':len(cand),'bindings':bind,'lineage_pass':True,'ambiguity_assessed_before_candidate_filter':True,'I_boundary_unknown':True,'accounting_period_date_key_not_economic_event':True,'protected_rows_local_exported':False,'aggregate_sha256':sha(out/'metadata_v2_aggregate.csv')};(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
