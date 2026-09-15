"""Custodian-only, seed-filtered outcome-blind event-date envelope.

No IBES extraction occurs here.  New historical CUSIPs are reported as a delta
and deliberately excluded from the already-pinned v2 metadata population.
"""
import argparse, hashlib, json, re
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from linkage_contract import valid_at, envelope_status

SEED_SHA='0c5d9175d53e76d746777776c2ff3ee46cc038f7227120eb22e86077a6d05555'
METADATA_SHA='97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb'
BRIDGE_SHA='fd259ac817ab9ea64553e0cdacadc22fcd94de361d1f1851855f9e27ed87e326'
CANDIDATE_SHA='68f39fbb19803dc2c63ecaf0754a1b9c900c27af1ec5ba3fd1b3d84764ce3d87'
LINK_COLS=['permno','ncusip','sdate','edate','score']
EVENT_KEYS=['cusip','pends','pdicity','anndats','anntims','actdats','acttims','source_partition']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def seed_filtered_links(seed, bridge):
 """The sole bridge reader: predicate-pushes the seed PERMNO envelope."""
 s=pd.read_csv(seed,usecols=['permno'],dtype={'permno':'Int64'})
 permnos=sorted(int(x) for x in s.permno.dropna().unique())
 return filter_links_to_seed(pq.read_table(bridge,columns=LINK_COLS,filters=[('permno','in',permnos)]).to_pandas(), set(permnos)), set(permnos)
def filter_links_to_seed(links, seed_permnos):
 """Second guard after predicate pushdown; no non-seed row may survive."""
 x=links.copy(); x['permno']=pd.to_numeric(x.permno,errors='coerce').astype('Int64')
 return x[x.permno.isin(seed_permnos)].copy()
def normalize_cusips(x):
 z=x.astype('string').str.strip().str.upper()
 return z[z.str.fullmatch(r'[A-Z0-9]{8}',na=False)]
def join_events_to_seed_links(events, links):
 """Events join only to the explicit normalized seed-link CUSIP key."""
 return events.merge(links,on='cusip',how='left')
def main():
 ap=argparse.ArgumentParser();
 ap.add_argument('--seed',type=Path,required=True);ap.add_argument('--metadata',type=Path,required=True);ap.add_argument('--bridge',type=Path,required=True);ap.add_argument('--v2-cusips',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args()
 if (sha(a.seed),sha(a.metadata),sha(a.bridge),sha(a.v2_cusips)) != (SEED_SHA,METADATA_SHA,BRIDGE_SHA,CANDIDATE_SHA): raise ValueError('pinned input hash mismatch')
 if a.out_dir.exists(): raise FileExistsError('new SCC output directory required')
 a.out_dir.mkdir(parents=True)
 links, seed_permnos=seed_filtered_links(a.seed,a.bridge)
 assert set(pd.to_numeric(links.permno,errors='coerce').dropna().astype(int)) <= seed_permnos
 links['ncusip']=links.ncusip.astype('string').str.strip().str.upper(); links=links[links.ncusip.str.fullmatch(r'[A-Z0-9]{8}',na=False)].copy(); links['cusip']=links['ncusip']
 old=set(normalize_cusips(pd.read_csv(a.v2_cusips,usecols=['cusip']).cusip)); historical=set(links.ncusip); new=historical-old
 pd.DataFrame({'ncusip':sorted(new)}).to_csv(a.out_dir/'new_historical_cusip_delta.csv',index=False)
 # Retain v2 only.  New identifiers are not sent to any IBES reader.
 e=pd.read_csv(a.metadata,usecols=EVENT_KEYS,dtype=str); e['cusip']=e.cusip.astype('string').str.strip().str.upper(); e=e[e.cusip.isin(old)].copy()
 x=join_events_to_seed_links(e,links); x['date_valid']=x.apply(lambda r:valid_at(r.sdate,r.edate,r.anndats),axis=1)
 v=x[x.date_valid].copy(); n=v.groupby(EVENT_KEYS).size().rename('pit_link_count').reset_index(); b=e.merge(n,on=EVENT_KEYS,how='left'); b['pit_link_count']=b.pit_link_count.fillna(0).astype(int)
 b['link_status']=b.apply(lambda r:envelope_status(r.pit_link_count,bool(r.anndats),bool(r.anntims),False),axis=1)
 b.to_csv(a.out_dir/'event_date_envelope.csv',index=False)
 date_ok=int(pd.to_datetime(b.anndats,errors='coerce').notna().sum()); time_ok=int(b.anntims.astype('string').str.match(r'^\s*\d{1,2}:?\d{2}',na=False).sum())
 receipt={'query_sha256':sha(Path(__file__)),'linkage_contract_sha256':sha(Path(__file__).with_name('linkage_contract.py')),'seed_sha256':sha(a.seed),'metadata_sha256':sha(a.metadata),'bridge_sha256':sha(a.bridge),'v2_candidate_sha256':sha(a.v2_cusips),'seed_permnos':len(seed_permnos),'seed_filtered_bridge_rows':len(links),'historical_cusips':len(historical),'v2_cusips':len(old),'new_historical_cusip_delta_count':len(new),'new_historical_cusip_delta_sha256':sha(a.out_dir/'new_historical_cusip_delta.csv'),'v2_records_retained':len(b),'records_with_date_valid_seed_link':int((b.pit_link_count>0).sum()),'ambiguous_link_records':int((b.pit_link_count>1).sum()),'parseable_announcement_dates':date_ok,'clock_string_pattern_records':time_ok,'pdicity_counts':b.pdicity.value_counts(dropna=False).to_dict(),'economic_event_count':None,'session_census':'NOT_RUN_TIMEZONE_AND_EXCHANGE_INTERVAL_SEMANTICS_UNVERIFIED','outcome_fields_read':False}
 (a.out_dir/'event_calendar_aggregate_receipt.json').write_text(json.dumps(receipt,indent=2,default=int)+'\n')
if __name__=='__main__': main()
