import datetime,hashlib,json,os
from pathlib import Path
D=Path.home()/'migration/reuse_first_20261115/run01/benchmark20'
p=D/'RUN_STATUS_PUBLIC.json';s=json.loads(p.read_text());pid=s.get('pid')
report={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'worker_process_exists':bool(pid and Path('/proc',str(pid)).exists()),'run':s}
if (D/'ATTEMPTS_PRIVATE.jsonl').exists():
 events={}
 for l in (D/'ATTEMPTS_PRIVATE.jsonl').read_text().splitlines():
  e=json.loads(l);events[(e['ordinal'],e['attempt'])]=e
 report['http_status_counts']={str(code):sum(e.get('http_status')==code for e in events.values()) for code in set(e.get('http_status') for e in events.values())}
 report['actual_models']=list({e['returned_model'] for e in events.values() if e.get('returned_model')})
 report['effective_token_limits']=list({e['rate_headers']['x-ratelimit-limit-tokens'] for e in events.values() if e.get('rate_headers',{}).get('x-ratelimit-limit-tokens')})
 # Error category names only. No error bodies, ad identities or private text.
 errors={}
 for f in (D/'results').glob('case*/ERRORS_PRIVATE.jsonl'):
  for line in f.read_text().splitlines():
   e=json.loads(line)
   if isinstance(e,dict):
    for k in ('code','error_code','error_type'):
     if isinstance(e.get(k),str) and len(e[k])<100:errors[e[k]]=errors.get(e[k],0)+1
 report['validator_error_codes']=errors
print(json.dumps(report,separators=(',',':')))
