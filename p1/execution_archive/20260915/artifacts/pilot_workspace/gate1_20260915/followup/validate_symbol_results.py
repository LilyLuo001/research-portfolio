"""Validate every UTC date touched by the isolated repair window, not just start."""
import csv,json,hashlib
from datetime import datetime,timedelta
from pathlib import Path
O=Path(__file__).resolve().parent
responses=json.loads((O/'free_symbology_responses.json').read_text())
by={r['query']['dataset']:r for r in responses}
with (O/'CRD_CLASS_B_REPAIR_REQUESTS.csv').open(newline='') as f:rows=list(csv.DictReader(f))
checks=[]
for r in rows:
    a=datetime.fromisoformat(r['start'].replace('Z','+00:00')); b=datetime.fromisoformat(r['end'].replace('Z','+00:00'))
    dates=[];d=a.date();last=(b-timedelta(microseconds=1)).date()
    while d<=last:dates.append(d.isoformat());d+=timedelta(days=1)
    response=by[r['dataset']]
    intervals=response.get('response',{}).get('result',{}).get(r['proposed_symbol'],[])
    ids=[{v['s'] for v in intervals if v['d0']<=d<v['d1']} for d in dates]
    checks.append(dict(repair_id=r['repair_id'],dataset=r['dataset'],proposed_symbol=r['proposed_symbol'],utc_dates=len(dates),dates_with_unique_mapping=sum(len(x)==1 for x in ids),dates_unmapped=sum(not x for x in ids),dates_ambiguous=sum(len(x)>1 for x in ids),status='FULL_DATE_INTERVAL_MAPPED' if all(len(x)==1 for x in ids) else 'MAPPING_GAP'))
with (O/'repair_mapping_validation.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
receipt=dict(status='MAPPING_VALIDATED_NOT_DOWNLOADED',windows=len(checks),all_dates_mapped_windows=sum(r['status']=='FULL_DATE_INTERVAL_MAPPED' for r in checks),gap_windows=sum(r['status']=='MAPPING_GAP' for r in checks),free_api_calls=4,download_calls=0,quote_record_coverage='NOT_ESTABLISHED_BY_SYMBOLOGY',response_sha256=hashlib.sha256((O/'free_symbology_responses.json').read_bytes()).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(O/'repair_mapping_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
