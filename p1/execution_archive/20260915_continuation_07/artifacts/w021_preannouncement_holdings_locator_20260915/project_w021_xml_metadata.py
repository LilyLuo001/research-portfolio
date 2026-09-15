#!/usr/bin/env python3
import csv, hashlib, json, re, xml.etree.ElementTree as ET
from pathlib import Path
SRC=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_repair_20260915/raw/primary_doc.xml')
OUT=SRC.parent.parent/'projection_v2'
EXPECTED_SHA='cb68bd2cd53956060fd3d27a3224450628ff5e086580b1d992ee172a2f86aa2d'
def candidate(units,cat,payoff,cusip,balance):
 try: positive=float(balance)>0
 except (TypeError,ValueError): positive=False
 return bool(units=='NS' and cat in ('','EC') and payoff in ('','Long') and positive and re.fullmatch(r'[A-Z0-9]{9}',cusip) and len(set(cusip))>1)
def ln(t): return t.rsplit('}',1)[-1]
def node(p,n): return next((x for x in p.iter() if ln(x.tag)==n),None)
def txt(p,n):
 x=node(p,n); return (x.text or '').strip() if x is not None and x.text else ''
def ident(p,k):
 x=node(p,'identifiers')
 if x is None:return ''
 for y in x.iter():
  if ln(y.tag)==k:return (y.attrib.get('value') or y.text or '').strip()
 return ''
def main():
 assert hashlib.sha256(SRC.read_bytes()).hexdigest()==EXPECTED_SHA, 'Unapproved source bytes'
 OUT.mkdir(parents=True,exist_ok=True); root=ET.parse(SRC).getroot(); gen=node(root,'genInfo')
 series,report=txt(gen,'seriesId'),txt(gen,'repPdDate'); accession='0001752724-22-263385'
 assert (series,report)==('S000032550','2022-09-30'), 'Source identity/date mismatch'
 rows=[]; rx=re.compile(r'^[A-Z0-9]{9}$')
 for i,s in enumerate((x for x in root.iter() if ln(x.tag)=='invstOrSec'),1):
  units=txt(s,'units'); cat=txt(s,'assetCat'); payoff=txt(s,'payoffProfile'); cusip=txt(s,'cusip').upper()
  bal=txt(s,'balance')
  rows.append({'series_id':series,'report_date':report,'accession':accession,'position_index':i,'cusip':cusip,'isin':ident(s,'isin'),'security_title':txt(s,'title'),'issuer_name':txt(s,'name'),'units':units,'assetcat':cat,'payoffprofile':payoff,'country':txt(s,'invCountry'),'rawsharebalance':bal,'common_equity_candidate':str(candidate(units,cat,payoff,cusip,bal)).lower()})
 fields=list(rows[0]) if rows else ['series_id','report_date','accession']
 with open(OUT/'w021_projection.csv','w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
 receipt={'status':'PASS','series_id':series,'report_date':report,'accession':accession,'positions':len(rows),'common_equity_candidates':sum(r['common_equity_candidate']=='true' for r in rows),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'projection_sha256':hashlib.sha256((OUT/'w021_projection.csv').read_bytes()).hexdigest(),'financial_value_fields_absent':True,'source_immutable':True}
 (OUT/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt))
if __name__=='__main__':main()
