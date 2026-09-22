#!/usr/bin/env python3
"""Exact 18-request mbp-1 acquisition. Key must exist only in SCC env."""
import os,json
from decimal import Decimal
from pathlib import Path
import databento as db
OUT=Path('/scratch/qluo/native_tick_pilot_20260922'); CAP=Decimal('10')
# A: announcement candidates; B: next-session RTH; C: fifth-prior-session RTH.
W=[('XOM_JAN','XOM','2023-01-31T11:23:00Z','2023-01-31T11:36:05Z'),('XOM_JAN_RTH','XOM','2023-01-31T14:58:00Z','2023-01-31T16:01:05Z'),('XOM_JAN_CTRL','XOM','2023-01-24T14:58:00Z','2023-01-24T16:01:05Z'),('AAPL_FEB','AAPL','2023-02-02T21:23:00Z','2023-02-02T21:36:05Z'),('AAPL_FEB_RTH','AAPL','2023-02-03T14:58:00Z','2023-02-03T16:01:05Z'),('AAPL_FEB_CTRL','AAPL','2023-01-27T14:58:00Z','2023-01-27T16:01:05Z'),('AAPL_AUG','AAPL','2023-08-03T20:23:00Z','2023-08-03T20:36:05Z'),('AAPL_AUG_RTH','AAPL','2023-08-04T13:58:00Z','2023-08-04T15:01:05Z'),('AAPL_AUG_CTRL','AAPL','2023-07-28T13:58:00Z','2023-07-28T15:01:05Z')]
def main():
 OUT.mkdir(parents=True,exist_ok=True);req=[]
 for name,stock,start,end in W:
  for dataset in ['XNAS.ITCH','ARCX.PILLAR']:req.append({'name':name,'dataset':dataset,'schema':'mbp-1','symbols':[stock,'SPY'],'start':start,'end':end,'path':str(OUT/f'{name}_{dataset.replace(".","_")}_mbp1.dbn.zst')})
 (OUT/'REQUEST_MANIFEST.json').write_text(json.dumps(req,indent=2)+'\n')
 if not os.environ.get('DATABENTO_API_KEY'):raise RuntimeError('inject DATABENTO_API_KEY only into SCC environment')
 c=db.Historical(os.environ['DATABENTO_API_KEY']);total=Decimal('0')
 for r in req:r['quoted_cost_usd']=str(c.metadata.get_cost(dataset=r['dataset'],schema=r['schema'],symbols=r['symbols'],start=r['start'],end=r['end'],stype_in='raw_symbol'));total+=Decimal(r['quoted_cost_usd'])
 (OUT/'COST_QUOTE.json').write_text(json.dumps({'quoted_total_usd':str(total),'hard_cap_usd':str(CAP),'requests':req},indent=2)+'\n')
 if total>CAP:raise RuntimeError(f'cap: {total}>{CAP}; no get_range called')
 for r in req:
  p=Path(r['path'])
  if not p.exists():c.timeseries.get_range(dataset=r['dataset'],schema='mbp-1',symbols=r['symbols'],start=r['start'],end=r['end'],stype_in='raw_symbol',stype_out='instrument_id',path=p)
 (OUT/'DOWNLOAD_RECEIPT.json').write_text(json.dumps({'quoted_total_usd':str(total),'request_count':len(req),'files':[r['path'] for r in req]},indent=2)+'\n')
if __name__=='__main__':main()
