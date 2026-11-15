"""Read-only compact refresh; no model calls, retries, or worker start."""
import base64, collections, datetime, hashlib, json, os, zlib
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';D=B/'qualification500_v1/luna_revision002'
def read(p):return json.loads(p.read_bytes())
state=read(D/'RUN_STATUS_PUBLIC.json');events={}
p=D/'ATTEMPTS_PRIVATE.jsonl'
if p.exists():
    for line in p.open():
        try:e=json.loads(line)
        except json.JSONDecodeError:continue
        events[e['ordinal'],e['attempt']]=e
results=[read(p) for p in sorted((D/'results').glob('case*/RESULT_PUBLIC.json'))]
headers=collections.Counter()
for x in events.values():
    value=x.get('rate_headers',{}).get('x-ratelimit-limit-tokens')
    if value:headers[value]+=1
status={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_status':state,'process_alive':(Path('/proc')/str(state['pid'])).exists(),'actual_saved_case_results':len(results),'saved_case_outcomes':dict(collections.Counter(x['status'] for x in results)),'physical_attempts_from_log':len(events),'http_status_counts':dict(collections.Counter(str(x.get('http_status','awaiting')) for x in events.values())),'rate_limit_tokens_header_counts':dict(headers),'new_production_accepted':0,'independent_new_Kimi_or_GPT_calls_this_wave':0,'stage4_locked':True,'paper_paused':True,'poll_action_read_only':True}
(B/'LATEST_QUALIFICATION_STATUS_PUBLIC.json').write_text(json.dumps(status,indent=2)+'\n')
obj={'LATEST_QUALIFICATION_STATUS_PUBLIC.json':status}
for name,rel in [('GAP_REGISTER_PUBLIC.json','GAP_REGISTER_PUBLIC.json'),('RECORDS_SOURCE_DEDUP_PUBLIC.json','stage1/RECORDS_SOURCE_DEDUP_PUBLIC.json'),('FIELD_COVERAGE_REGISTER_PUBLIC.json','FIELD_COVERAGE_REGISTER_PUBLIC.json')]:
    p=B/rel
    if p.exists():obj[name]=read(p)
encoded=base64.b64encode(zlib.compress(json.dumps(obj).encode(),9)).decode();assert len(encoded)<3800
print(json.dumps({'aggregate_zlib_b64':encoded}))
