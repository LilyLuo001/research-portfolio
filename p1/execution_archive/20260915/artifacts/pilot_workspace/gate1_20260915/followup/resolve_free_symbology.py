"""Allowlisted free symbology only. Never downloads or orders data."""
import json,os
from pathlib import Path
O=Path(__file__).resolve().parent
if not os.environ.get('DATABENTO_API_KEY'):
    print('NOT_RUN_AUTH_ENV_ABSENT; historical data availability remains UNKNOWN')
    raise SystemExit(0)
import databento as db
queries=json.loads((O/'FREE_SYMBOLOGY_QUERIES.json').read_text())
assert len(queries)==4
results=[]
for q in queries:
    assert set(q)=={'dataset','symbols','stype_in','stype_out','start_date','end_date'}
    try:
        r=db.Historical(key=os.environ['DATABENTO_API_KEY']).symbology.resolve(**q)
        results.append(dict(query=q,status='RESPONSE_RECEIVED',response=r))
    except Exception as exc:
        results.append(dict(query=q,status='QUERY_FAILED',error_type=type(exc).__name__))
(O/'free_symbology_responses.json').write_text(json.dumps(results,indent=2,default=str)+'\n')
print(json.dumps([dict(dataset=r['query']['dataset'],status=r['status']) for r in results]))
