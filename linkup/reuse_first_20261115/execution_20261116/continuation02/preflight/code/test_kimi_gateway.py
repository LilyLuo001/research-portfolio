"""Synthetic-only gateway audit. AST replaces private input path and bundle before execution.
No Azure/OpenCode calls, no source advertisements, no credentials.
"""
import ast,hashlib,http.client,http.server,io,json,tempfile,threading,time,types,urllib.error
from pathlib import Path
P=Path(__file__).parent;SOURCE=P/'kimi_gateway.py'
TEXT=SOURCE.read_text();TASK='synthetic_case'
ROW={'record_id':'synthetic-audit','context_sha256':'a'*64,'full_document':'Synthetic record only.'}
class FakeResponse(io.BytesIO):
 def __init__(self,status=200,body=None,headers=None):
  if body is None:
   body=b'data: '+json.dumps({'choices':[{'delta':{'reasoning_content':'SYNTHETIC_PRIVATE_REASONING_NOT_TO_LOG'},'finish_reason':None}]}).encode()+b'\n\ndata: '+json.dumps({'choices':[{'delta':{'content':'{"ok":true}'},'finish_reason':'stop'}]}).encode()+b'\n\ndata: '+json.dumps({'choices':[],'usage':{'prompt_tokens':123,'completion_tokens':456,'total_tokens':579}}).encode()+b'\n\ndata: [DONE]\n\n'
  super().__init__(body);self.status=status;self.headers=headers or {'Content-Type':'text/event-stream','x-ratelimit-limit-tokens':'300000'}
class FakeOpener:
 def __init__(self,responses):self.responses=list(responses);self.requests=[]
 def open(self,req,timeout=None):
  self.requests.append(req);v=self.responses.pop(0)
  if isinstance(v,Exception):raise v
  return v

def fixture(tmp,responses):
 tree=ast.parse(TEXT)
 for node in tree.body:
  if isinstance(node,ast.Assign):
   names=[x.id for x in node.targets if isinstance(x,ast.Name)]
   if names==['W']:node.value=ast.parse(f'Path({str(tmp)!r})',mode='eval').body
   if names==['BUNDLE']:node.value=ast.parse(repr({'items':[{'case':TASK,'qualification_task':'synthetic_task','row':ROW}], 'instructions':'Synthetic frozen instructions','schema':{'type':'object'}}),mode='eval').body
 ast.fix_missing_locations(tree)
 env={'__name__':'synthetic_audit_no_main'};exec(compile(tree,str(SOURCE),'exec'),env)
 env['OPENER']=opener=FakeOpener(responses)
 env['time']=types.SimpleNamespace(monotonic=time.monotonic,time=time.time,sleep=lambda *_:None)
 (tmp/'INPUT_BUNDLE_PRIVATE.json.gz').write_bytes(b'synthetic')
 (tmp/'ALLOW_INFERENCE_PRIVATE.json').write_text(json.dumps({'status':'candidate_finished_serial_reference_authorized','expires_epoch':time.time()+3600,'input_bundle_sha256':hashlib.sha256(b'synthetic').hexdigest()}))
 (tmp/'EXCLUSIONS_PRIVATE.json').write_text(json.dumps({'tasks':[],'context_sha256':[]}))
 env['reserve']=lambda n:None
 server=http.server.ThreadingHTTPServer(('.'.join(map(str,(127,0,0,1))),0),env['Handler']);server.daemon_threads=True;server.env=env
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 return env,opener,server

def request(server,mutate=None):
 data={'model':'linkup-kimi-k3-1-pro','stream':True,'max_completion_tokens':999999,'max_tokens':999999,
       'messages':[{'role':'user','content':server.env['expected_prompt'](TASK)}]}
 if mutate:mutate(data)
 conn=http.client.HTTPConnection('.'.join(map(str,(127,0,0,1))),server.server_port,timeout=3)
 raw=json.dumps(data).encode();conn.request('POST','/qualification350/openai/v1/chat/completions',body=raw,headers={'Authorization':'Bearer SYNTHETIC_DUMMY_NOT_REAL_CREDENTIAL','Content-Type':'application/json'})
 r=conn.getresponse();status=r.status;body=r.read();conn.close();return status,body

def run():
 passed=[]
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[FakeResponse()])
  try:
   s,b=request(server);assert s==200 and b'[DONE]' in b;passed.append('SSE_forwarded')
   sent=json.loads(opener.requests[0].data);assert sent['max_tokens']==16000 and 'max_completion_tokens' not in sent and sent['stream_options']['include_usage'];passed.append('max_tokens_and_usage_enforced')
   # Handler state is persisted by the time close-delimited response reaches EOF.
   logs=(Path(d)/'GATEWAY_ATTEMPTS_PRIVATE.jsonl').read_text();e=json.loads(logs.splitlines()[-1]);assert e['raw_usage']=={'prompt_tokens':123,'completion_tokens':456,'total_tokens':579};passed.append('raw_usage_preserved')
   assert 'SYNTHETIC_DUMMY' not in logs and 'SYNTHETIC_PRIVATE_REASONING' not in logs and ROW['full_document'] not in logs;passed.append('credential_reasoning_source_not_logged')
   assert request(server)[0]==409 and len(opener.requests)==1;passed.append('completed_duplicate_blocked')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[urllib.error.URLError('synthetic transport uncertainty')])
  try:
   assert request(server)[0]==409;assert request(server)[0]==409;assert len(opener.requests)==1;passed.append('uncertain_submission_never_retried')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[FakeResponse(429,b'{"error":{"code":"synthetic_rate_limit"}}',{'Content-Type':'application/json','retry-after-ms':'250'}),FakeResponse()])
  try:
   assert request(server)[0]==429;assert request(server)[0]==200;assert len(opener.requests)==2;passed.append('confirmed_429_then_bounded_retry')
   assert env['STATE'][TASK]['attempt']==2;passed.append('attempt_count_durable')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[])
  try:
   assert request(server,lambda data:data.update(model='unapproved'))[0]==400;assert not opener.requests;passed.append('wrong_model_rejected_without_upstream')
   assert request(server,lambda data:data['messages'][0].update(content=data['messages'][0]['content'].replace(ROW['full_document'],'altered')))[0]==400;assert not opener.requests;passed.append('altered_source_rejected_without_upstream')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[FakeResponse(500,b'{"error":{"code":"content_filter"}}',{'Content-Type':'application/json'})])
  try:
   assert request(server)[0]==500;assert request(server)[0]==409;assert len(opener.requests)==1;passed.append('provider_filter_5xx_never_retried')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  body=b'data: {"choices":[{"delta":{},"finish_reason":"content_filter"}]}\n\ndata: [DONE]\n\n'
  env,opener,server=fixture(Path(d),[FakeResponse(200,body)])
  try:
   assert request(server)[0]==200;assert env['STATE'][TASK].get('provider_content_filter') is True;assert request(server)[0]==409;assert len(opener.requests)==1;passed.append('SSE_content_filter_explicitly_quarantined')
  finally:server.shutdown();server.server_close()
 for name in ('EXCLUSIONS_PRIVATE.json',):
  with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
   env,opener,server=fixture(Path(d),[]);(Path(d)/name).write_text(json.dumps({'tasks':['synthetic_task']}))
   try:
    assert request(server)[0]==409 and not opener.requests;passed.append(name.removesuffix('_PRIVATE.json').lower()+'_blocked_before_upstream')
   finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-offline-') as d:
  env,opener,server=fixture(Path(d),[FakeResponse(429,b'{"error":{"code":"synthetic_rate_limit"}}',{'Content-Type':'application/json'}) for _ in range(4)])
  try:
   assert [request(server)[0] for _ in range(3)]==[429,429,409];assert len(opener.requests)==2;passed.append('physical_attempt_limit_two_enforced')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-budget-') as d:
  env,opener,server=fixture(Path(d),[])
  try:
   env['ATTEMPTS'][('old',1)]={'reservation_usd':135.0}
   assert request(server)[0]==409 and not opener.requests;passed.append('persisted_dollar_cap_before_forward')
   assert not env['budget_allows'](0.01,{('old',1):{'reservation_usd':134.999}});passed.append('conservative_reservations_do_not_disappear')
  finally:server.shutdown();server.server_close()
 with tempfile.TemporaryDirectory(prefix='linkup-gateway-lease-') as d:
  env,opener,server=fixture(Path(d),[])
  try:
   p=Path(d)/'ALLOW_INFERENCE_PRIVATE.json';x=json.loads(p.read_text());x['expires_epoch']=0;p.write_text(json.dumps(x))
   assert request(server)[0]==409 and not opener.requests;passed.append('expired_serial_lease_no_call')
  finally:server.shutdown();server.server_close()
 return {'source_sha256':hashlib.sha256(TEXT.encode()).hexdigest(),'passed':len(passed),'tests':passed,'real_model_calls':0,'private_source_read':False,'scope':'gateway synthetic HTTP boundary only; not semantic quality certification'}
if __name__=='__main__':
 r=run();(P/'GATEWAY_SYNTHETIC_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
