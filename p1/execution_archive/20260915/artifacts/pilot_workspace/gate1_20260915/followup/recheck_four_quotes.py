"""Only free metadata cost/count checks for four previously excluded jobs."""
import csv,json,os
from datetime import datetime,timezone
from pathlib import Path
import databento as db
O=Path(__file__).resolve().parent
A=O.parents[1]/'missing_data_round_20260914/databento_final_acquisition'
allowed={'ALTJOB_00186','ALTJOB_01420','ALTJOB_01748','COREJOB_00366'}
if not os.environ.get('DATABENTO_API_KEY'):raise SystemExit('NOT_RUN_AUTH_ENV_ABSENT')
with (A/'quote_jobs.csv').open(newline='') as f:jobs=[r for r in csv.DictReader(f) if r['job_id'] in allowed]
assert len(jobs)==4 and {r['job_id'] for r in jobs}==allowed
c=db.Historical(key=os.environ['DATABENTO_API_KEY']);out=[]
for r in jobs:
    q=dict(dataset=r['dataset'],schema=r['schema'],symbols=r['symbols'].split(';'),stype_in='raw_symbol',start=r['start'],end=r['end'])
    v=dict(job_id=r['job_id'],query=q,original_status=r['status'],status='METADATA_ONLY_NOT_DOWNLOADED')
    for name,method in [('cost',c.metadata.get_cost),('record_count',c.metadata.get_record_count)]:
        try:v[name]=method(**q)
        except Exception as e:v[name+'_error_type']=type(e).__name__
    out.append(v)
(O/'four_quote_recheck.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),results=out,download_calls=0),indent=2,default=str)+'\n')
print(json.dumps([dict(job_id=r['job_id'],cost=r.get('cost'),record_count=r.get('record_count'),errors=[k for k in r if k.endswith('_error_type')]) for r in out]))
