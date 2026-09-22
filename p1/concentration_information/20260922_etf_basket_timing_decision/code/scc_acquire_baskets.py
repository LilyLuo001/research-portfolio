#!/usr/bin/env python3
"""SCC-only exact basket BBO acquisition; requires externally injected env key."""
import os,json,glob,hashlib
from decimal import Decimal
from pathlib import Path
from datetime import datetime,timedelta
import duckdb,databento as db
ROOT=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared')
OUT=Path('/scratch/qluo/etf_basket_timing_20260922')
EVENTS=[('P1-2023-08-01','2022-12-31','2023-01-31T11:30:00Z'),('P1-2023-08-03','2023-06-30','2023-07-28T10:00:00Z'),('P1-2023-06-02','2023-03-31','2023-04-14T09:55:00Z'),('P1-2023-01-01','2022-12-31','2023-02-02T21:30:00Z'),('P1-2023-01-03','2023-06-30','2023-08-03T20:30:00Z'),('P1-2023-02-02','2023-03-31','2023-04-25T20:07:00Z')]
def main():
 OUT.mkdir(parents=True,exist_ok=True); paths=glob.glob(str(ROOT/'raw/rescue_remaining/crsp_holdings_etf_202*'/'part_*.parquet')); c=duckdb.connect();q='['+','.join(repr(x) for x in paths)+']'; c.execute(f'create view h as select report_dt,crsp_portno,ticker,nbr_shares,percent_tna from read_parquet({q})')
 rows=[]
 for eid,report,anchor in EVENTS:
  sy=[x[0] for x in c.execute("select distinct upper(trim(ticker)) from h where crsp_portno=1021980 and cast(report_dt as date)=cast(? as date) and ticker is not null and nbr_shares>0",[report]).fetchall()]
  a=datetime.fromisoformat(anchor.replace('Z','+00:00'));start=(a-timedelta(minutes=15)).isoformat();end=(a+timedelta(minutes=75)).isoformat()
  # July has two predeclared anchors (10:00 and 10:30 UTC): one union request.
  if eid=='P1-2023-08-03': start='2023-07-28T09:45:00+00:00';end='2023-07-28T11:45:00+00:00'
  for dataset in ['XNAS.ITCH','ARCX.PILLAR']: rows.append({'event_id':eid,'report_date':report,'dataset':dataset,'schema':'bbo-1s','symbols':sy,'symbol_count':len(sy),'start':start,'end':end,'path':str(OUT/f'{eid}_{dataset.replace(".","_")}.dbn.zst')})
 (OUT/'BASKET_REQUEST_MANIFEST.json').write_text(json.dumps(rows,indent=2)+'\n')
 if not os.environ.get('DATABENTO_API_KEY'): raise RuntimeError('DATABENTO_API_KEY must be injected into this SCC process; it is not read or written by this script')
 cl=db.Historical(os.environ['DATABENTO_API_KEY']); receipt=[]; cap=Decimal('100'); total=Decimal('0')
 for r in rows:
  try:
   cost=Decimal(str(cl.metadata.get_cost(dataset=r['dataset'],schema=r['schema'],symbols=r['symbols'],start=r['start'],end=r['end'],stype_in='raw_symbol'))); r['quoted_cost_usd']=str(cost);total+=cost
  except Exception as e: r['quote_error']=type(e).__name__+': '+str(e)
  receipt.append({k:v for k,v in r.items() if k!='symbols'})
 quote={'quoted_total_usd':str(total),'hard_cap_usd':str(cap),'requests':receipt}
 (OUT/'BASKET_COST_QUOTE.json').write_text(json.dumps(quote,indent=2)+'\n')
 if total>cap: raise RuntimeError(f'quoted total {total} exceeds hard cap {cap}; no downloads started')
 for r in rows:
  p=Path(r['path'])
  if r.get('quote_error'): r['download_status']='SKIPPED_QUOTE_ERROR';continue
  if not p.exists(): cl.timeseries.get_range(dataset=r['dataset'],schema=r['schema'],symbols=r['symbols'],start=r['start'],end=r['end'],stype_in='raw_symbol',stype_out='instrument_id',path=p)
  r['bytes']=p.stat().st_size; r['sha256']=hashlib.sha256(p.read_bytes()).hexdigest(); r.pop('symbols',None)
 (OUT/'BASKET_DOWNLOAD_RECEIPT.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
