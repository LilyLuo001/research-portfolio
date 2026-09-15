#!/usr/bin/env python3
"""Select and parse cached N-PORT reports strictly before package cutoffs.

This is an acquisition-stage build.  Cutoffs are deliberately conservative
and retain their evidence status; they are not a final scientific sign-off.
Only the five P1 decision-pilot packages are included.  W021 contains JPEF's
equity predecessor only; the date-coincident bond conversion is excluded.
"""
from __future__ import annotations
import csv, hashlib, json, re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

OUT=Path(__file__).resolve().parent
CACHE=Path('/Users/lilyluo/research-portfolio/p1/t2_free/cache/nport')
UNIVERSE=Path('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_universe_gate0_pass.csv')
PACKAGES={
 'W002':{'cutoff':'2020-11-16','status':'CONSERVATIVE_FIRST_PUBLIC_SEC_REGISTRATION_DATE',
  'source':'https://www.sec.gov/Archives/edgar/data/1816125/000179420220000482/form485a.htm',
  'series':{'S000016732','S000000972','S000000976','S000000977'}},
 'W013':{'cutoff':'2021-12-01','status':'CONSERVATIVE_MONTH_START_FROM_ISSUER_FIRST_ANNOUNCED_DECEMBER_2021',
  'source':'https://www.franklintempleton.com/press-releases/news-room/2022/franklin-templeton-converts-two-mutual-funds-to-etfs',
  'series':{'S000047047'}},
 'W016':{'cutoff':'2022-08-26','status':'PRIMARY_SOURCE_DATE_VERIFIED_TIME_UNCERTAIN',
  'source':'https://www.sec.gov/Archives/edgar/data/1592900/000182912622018075/easeriestrust_defa14a.htm',
  'series':{'S000030751'}},
 'W021':{'cutoff':'2023-02-07','status':'REPOSITORY_PRIMARY_SOURCE_DATE',
  'source':'https://www.sec.gov/Archives/edgar/data/1485894/000119312523067795/d429709dn14.htm',
  'series':{'S000032550'}},
 'W025':{'cutoff':'2023-06-14','status':'REPOSITORY_PRIMARY_SOURCE_DATE',
  'source':'https://www.sec.gov/Archives/edgar/data/945908/000119312523215546/d528044dn14.htm',
  'series':{'S000015911','S000015909','S000015910','S000019927','S000019928'}},
}

def lname(tag): return tag.split('}',1)[-1]
def first(parent,name): return next((x for x in parent.iter() if lname(x.tag)==name),None)
def text(parent,name):
 n=first(parent,name); return (n.text or '').strip() if n is not None else ''
def num(v):
 try:return float(v)
 except:return None
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ident(sec,kind):
 ids=first(sec,'identifiers')
 if ids is None:return ''
 for n in ids.iter():
  if lname(n.tag)==kind:return (n.attrib.get('value') or n.text or '').strip()
 return ''

def metadata(p):
 root=ET.parse(p).getroot(); gen=first(root,'genInfo')
 return {'series_id':text(gen,'seriesId'),'report_date':text(gen,'repPdDate'),'period_end':text(gen,'repPdEnd')}

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 u=pd.read_csv(UNIVERSE,dtype=str)
 selected=[]
 for wave,spec in PACKAGES.items():
  for sid in spec['series']:
   rows=u[(u.wave_id==wave)&(u.pre_series_id==sid)]
   if len(rows)!=1: raise ValueError(f'{wave}/{sid}: expected one universe row, got {len(rows)}')
   base=rows.iloc[0].to_dict(); cik=str(int(float(base['pre_cik'])))
   candidates=[]
   for p in CACHE.glob(cik+'_*.xml'):
    try:m=metadata(p)
    except Exception:continue
    if m['series_id']==sid and m['report_date'] and m['report_date']<spec['cutoff']:
     candidates.append((m['report_date'],p,m))
   if not candidates: raise ValueError(f'{wave}/{sid}: no cached report before {spec["cutoff"]}')
   report_date,p,m=max(candidates,key=lambda x:(x[0],x[1].name))
   selected.append((wave,spec,sid,base,report_date,p,m,len(candidates)))
 holdings=[]; manifest=[]
 cusip_re=re.compile(r'^[A-Z0-9]{9}$')
 for wave,spec,sid,base,report_date,p,m,n_before in selected:
  root=ET.parse(p).getroot(); fund=first(root,'fundInfo'); positions=[]
  for pos,sec in enumerate((x for x in root.iter() if lname(x.tag)=='invstOrSec'),1):
   units=text(sec,'units'); cat=text(sec,'assetCat'); payoff=text(sec,'payoffProfile')
   balance=num(text(sec,'balance')); cusip=text(sec,'cusip').upper()
   common=bool(units=='NS' and cat in ('','EC') and payoff in ('','Long') and
               balance is not None and balance>0 and cusip_re.fullmatch(cusip) and len(set(cusip))>1)
   row={'wave_id':wave,'announcement_cutoff':spec['cutoff'],'announcement_cutoff_status':spec['status'],
    'announcement_source':spec['source'],'effective_date':base['effective_date'],'event_id':base['event_id'],
    'pre_series_id':sid,'pre_series_name':base['pre_series_name'],'pre_cik':int(float(base['pre_cik'])),
    'post_series_id':base['post_series_id'],'post_series_name':base['post_series_name'],
    'pre_report_date':report_date,'pre_accession':p.stem.split('_',1)[1],
    'cache_file':str(p),'position_number':pos,'issuer_name':text(sec,'name'),
    'security_title':text(sec,'title'),'cusip':cusip,'isin':ident(sec,'isin'),
    'nport_ticker':ident(sec,'ticker').upper(),'balance':balance,'units':units,
    'currency':text(sec,'curCd'),'position_value_usd':num(text(sec,'valUSD')),
    'pct_value_reported':num(text(sec,'pctVal')),'payoff_profile':payoff,'asset_category':cat,
    'investment_country':text(sec,'invCountry'),'is_common_equity_candidate':common,
    'raw_reported_shares':balance if units=='NS' else None,
    'fund_total_assets_usd':num(text(fund,'totAssets')) if fund is not None else None,
    'fund_net_assets_usd':num(text(fund,'netAssets')) if fund is not None else None}
   holdings.append(row); positions.append(row)
  manifest.append({'wave_id':wave,'pre_series_id':sid,'pre_series_name':base['pre_series_name'],
   'announcement_cutoff':spec['cutoff'],'announcement_cutoff_status':spec['status'],
   'announcement_source':spec['source'],'selected_report_date':report_date,
   'selected_accession':p.stem.split('_',1)[1],'selected_file_sha256':sha(p),
   'candidate_cached_reports_before_cutoff':n_before,'positions':len(positions),
   'common_equity_candidates':sum(x['is_common_equity_candidate'] for x in positions)})
 h=pd.DataFrame(holdings); m=pd.DataFrame(manifest)
 h.to_parquet(OUT/'strict_preannouncement_holdings.parquet',index=False)
 m.to_csv(OUT/'strict_preannouncement_filing_manifest.csv',index=False)
 receipt={'status':'BUILT_FROM_EXISTING_IMMUTABLE_CACHE','packages':list(PACKAGES),'series':len(m),
  'positions':len(h),'common_equity_candidates':int(h.is_common_equity_candidate.sum()),
  'holdings_sha256':sha(OUT/'strict_preannouncement_holdings.parquet'),
  'filing_manifest_sha256':sha(OUT/'strict_preannouncement_filing_manifest.csv'),
  'source_universe_sha256':sha(UNIVERSE),'raw_inputs_modified':False,
  'w021_bond_series_excluded':'S000003492','post_outcomes_read':False}
 (OUT/'strict_preannouncement_holdings_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
