"""Finite independent OpenCode reference leg; validation/comparison run in Azure.

No candidate answers are available to this worker. Preserve ambiguous submissions;
never re-post a prompt. Only the gateway can admit confirmed temporary retries.
"""
import base64,collections,concurrent.futures,datetime,fcntl,gzip,hashlib,json,os,subprocess,sys,threading,time,zlib
from pathlib import Path
from control import HERE,W,vm,save,sha
os.umask(0o077)
CLI=Path.home()/'Library/Application Support/ai.opencode.desktop/cli/2.2.7-arm64/opencode-cli'
BUNDLE=json.loads((W/'INPUT_BUNDLE_PRIVATE.json').read_text())
ITEMS=BUNDLE['items'];R=W/'records';R.mkdir(exist_ok=True)
LOCK=threading.RLock();STOP=threading.Event();START=time.time()
# Importing gateway only constructs policy; does not bind/listen or make requests.
import kimi_gateway as gateway
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def api(method,path,body=None):
 args=[str(CLI),'api',method,path]
 if body is not None:
  data=json.dumps(body,ensure_ascii=False);assert len(data.encode())<120000;args+=['--data',data]
 p=subprocess.run(args,cwd=W,capture_output=True,text=True,timeout=45)
 if p.returncode:raise RuntimeError('OpenCode_control_failed')
 return json.loads(p.stdout) if p.stdout.strip() else None
def get(path):
 for attempt in range(4):
  try:return api('GET',path)
  except Exception:
   if attempt==3:raise
   time.sleep(2**attempt)
def idle(x):
 t=x.get('time',{});return not t.get('busy') or t.get('idle',0)>=t['busy']
def events(case=None):
 latest={};p=W/'GATEWAY_ATTEMPTS_PRIVATE.jsonl'
 if p.exists():
  for line in p.read_text().splitlines():
   try:e=json.loads(line)
   except json.JSONDecodeError:continue
   if case is None or e['task']==case:latest[e['task'],e['attempt']]=e
 return list(latest.values())
def progress(phase):
 with LOCK:
  states=[json.loads(p.read_text()) for p in R.glob('*/EXECUTION_PRIVATE.json')];ev=events()
  commits=[json.loads(p.read_text()) for p in (W/'commits').glob('*/RECEIPT_PUBLIC.json')] if (W/'commits').exists() else []
  usage=[x.get('raw_usage') or {} for x in ev]
  result={'phase':phase,'at_utc':now(),'pid':os.getpid(),'selected':350,'submitted':sum(bool(x.get('submitted_at_utc')) for x in states),'finished':sum(bool(x.get('finished_at_utc')) for x in states),'cloud_validated':sum(x['records'] for x in commits),'cloud_frozen_pass_references':sum(x['frozen_pass'] for x in commits),'physical_attempts':len(ev),'reserved_usd':round(sum(x.get('reservation_usd',0) for x in ev),8),'input_tokens':sum(x.get('prompt_tokens',0) for x in usage),'output_tokens':sum(x.get('completion_tokens',0) for x in usage),'responses_without_usage':sum(not x for x in usage),'new_production_accepted':0,'elapsed_seconds_this_process':round(time.time()-START,2),'model':'Kimi-K3.1-Pro','rate_ceiling_tpm':240000,'deployment_limit_tpm':300000,'concurrent_sessions':4,'candidate_answers_read':False,'no_human_gold_claim':True}
  result['public_list_usage_estimate_usd']=(result['input_tokens']*2.3+result['output_tokens']*11.5)/1e6
  save(W/'RUN_STATUS_PUBLIC.json',result);save(HERE/'KIMI_RUN_STATUS_PUBLIC.json',result);return result
def lease(tag):
 answer=vm((HERE/'cloud_reference_lease.py').read_text(),tag)
 x=json.loads(zlib.decompress(base64.b64decode(answer['lease_zlib_b64'])))
 old=json.loads((W/'EXCLUSIONS_PRIVATE.json').read_text()) if (W/'EXCLUSIONS_PRIVATE.json').exists() else {}
 for k in ('tasks','context_sha256'):x['exclusions'][k]=sorted(set(x['exclusions'].get(k,[]))|set(old.get(k,[])))
 save(W/'EXCLUSIONS_PRIVATE.json',x['exclusions']);save(W/'ALLOW_INFERENCE_PRIVATE.json',x['permit'])
def run_one(index):
 item=ITEMS[index];case=str(item['case']);d=R/case;d.mkdir(exist_ok=True);p=d/'EXECUTION_PRIVATE.json'
 state=json.loads(p.read_text()) if p.exists() else {'case':case,'index':index,'status':'prepared_not_submitted'}
 if state.get('finished_at_utc'):return state
 try:
  assert not STOP.is_set(),'coordinator_stop'
  gateway.require_permit(case)
  prompt=gateway.expected_prompt(case)
  if not state.get('session_id'):
   digest=hashlib.sha256(('qualification500_v1/Kimi/'+case).encode()).hexdigest()[:24]
   sid='ses_linkupqual_'+digest;state.update(session_id=sid,prompt_id='msg_linkupqual_'+digest,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest());save(p,state)
   session=api('POST','/api/session',{'id':sid,'title':f'LinkUp independent qualification {index+1}/350','agent':'linkup-batch','model':{'providerID':'azure-kimi','id':'linkup-kimi-k3-1-pro'},'location':{'directory':str(W)},'permissions':[{'action':'*','resource':'*','effect':'deny'}],'metadata':{'scope':'qualification500_v1_blind_reference350','semantic_quality_certified':False}})['data']
  else:session=get('/api/session/'+state['session_id'])['data']
  sid=state['session_id'];assert session['model']=={'providerID':'azure-kimi','id':'linkup-kimi-k3-1-pro'} or (session['model']['providerID']=='azure-kimi' and session['model']['id']=='linkup-kimi-k3-1-pro')
  assert not session.get('parentID') and not session.get('fork') and session['permissions']==[{'action':'*','resource':'*','effect':'deny'}]
  if not state.get('submitted_at_utc'):
   assert not any(m.get('type') in ('user','assistant') for m in get(f'/api/session/{sid}/message')['data'])
   state.update(status='submission_started_reconcile_not_resubmit',submitted_at_utc=now());save(p,state)
   try:api('POST',f'/api/session/{sid}/prompt',{'id':state['prompt_id'],'text':prompt})
   except Exception:state['admission_uncertain']=True;save(p,state)
  for step in range(180):
   time.sleep(5);info=get('/api/session/'+sid)['data'];messages=get(f'/api/session/{sid}/message')['data'];assistants=[m for m in messages if m.get('type')=='assistant']
   if assistants and all(m.get('time',{}).get('completed') for m in assistants) and idle(info):break
  else:raise ValueError('timeout_preserved_no_resubmission')
  assert len(assistants)==1,'unexpected_assistant_count';m=assistants[0]
  # Transport visible output only. No hidden reasoning retained or parsed.
  visible={k:m.get(k) for k in ('model','finish','rawFinish','tokens','cost')}
  visible['content']=[{'type':c['type'],'text':c.get('text','')} for c in m.get('content',[]) if c['type']!='reasoning']
  if m.get('error'):visible['error']={'present':True}
  if m.get('retry'):visible['retry']={'present':True}
  state['visible']=visible
  attempts=events(case)
  for _ in range(10):
   if attempts and attempts[-1]['status'] not in ('forwarding_uncertain','reserved'):break
   time.sleep(.2);attempts=events(case)
  state['provider_filtered']=any(x.get('provider_content_filter') for x in attempts)
  if state['provider_filtered']:
   with LOCK:
    e=json.loads((W/'EXCLUSIONS_PRIVATE.json').read_text())
    e['tasks']=sorted(set(e.get('tasks',[]))|{item['qualification_task']});e['context_sha256']=sorted(set(e.get('context_sha256',[]))|{item['row']['context_sha256']});save(W/'EXCLUSIONS_PRIVATE.json',e)
  assert attempts and attempts[-1]['status']==200,'gateway_not_confirmed_complete'
  state['status']='transport_visible_saved'
 except Exception as error:
  allowed={'timeout_preserved_no_resubmission','gateway_not_confirmed_complete','coordinator_stop','quarantined_do_not_forward','serial_lease_expired','unexpected_assistant_count'}
  state['status']=str(error) if str(error) in allowed else 'transport_boundary_exception_preserved';state['error_type']=type(error).__name__
  if state.get('session_id') and state.get('submitted_at_utc'):
   try:
    if not idle(get('/api/session/'+state['session_id'])['data']):
     api('POST','/api/session/'+state['session_id']+'/interrupt')
     for _ in range(12):
      if idle(get('/api/session/'+state['session_id'])['data']):break
      time.sleep(5)
     else:raise RuntimeError('unconfirmed_orphan')
   except Exception:STOP.set();state['reconcile_required']=True
 finally:
  state['gateway_attempts']=events(case)
  state['provider_filtered']=bool(state.get('provider_filtered') or any(x.get('provider_content_filter') for x in state['gateway_attempts']))
  if not state.get('reconcile_required'):state['finished_at_utc']=now()
  save(p,state);progress('reference_leg_running')
 return state
def commit(records):
 assert all(x.get('finished_at_utc') and not x.get('reconcile_required') for x in records),'active_sessions_cannot_commit'
 name=f"batch{min(x['index'] for x in records):04d}_{len(records):02d}"
 dest=W/'commits'/name;dest.mkdir(parents=True,exist_ok=True);p=dest/'RECEIPT_PUBLIC.json'
 raw=json.dumps({'commit_id':name,'records':records},ensure_ascii=False,separators=(',',':')).encode()
 if p.exists():assert json.loads(p.read_text())['payload_sha256']==hashlib.sha256(raw).hexdigest();return
 source='PAYLOAD_B64='+repr(base64.b64encode(gzip.compress(raw,mtime=0)).decode())+'\n'+(HERE/'cloud_commit_references.py').read_text()
 # Split transport only, never repeat inference.
 wrapper_bytes=len(base64.b64encode(zlib.compress(source.encode(),9)))*4//3+1000
 if wrapper_bytes>=120000:
  assert len(records)>1,'single_output_requires_chunk_transfer';mid=len(records)//2;commit(records[:mid]);commit(records[mid:]);return
 answer=vm(source,'commit_'+name);assert answer['status']=='reference_batch_cloud_validated' and answer['payload_sha256']==hashlib.sha256(raw).hexdigest();save(p,answer)
def main():
 f=(W/'WORKER.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
 save(W/'WORKER_CODE_IDENTITY_PUBLIC.json',{'pid':os.getpid(),'at_utc':now(),'worker_sha256':sha(Path(__file__)),'gateway_sha256':sha(HERE/'kimi_gateway.py'),'cloud_commit_sha256':sha(HERE/'cloud_commit_references.py'),'input_bundle_sha256':sha(W/'INPUT_BUNDLE_PRIVATE.json.gz'),'prior_Luna_worker_not_restarted':True})
 assert len(ITEMS)==350 and len({str(x['case']) for x in ITEMS})==350
 lease('lease_start001')
 progress('reference_leg_starting');first=run_one(0);commit([first])
 assert first.get('gateway_attempts'),'first_route_did_not_reach_provider_stop'
 assert not STOP.is_set()
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  for offset in range(1,350,8):
   if STOP.is_set() or (W/'STOP_AFTER_BATCH').exists():break
   permit=json.loads((W/'ALLOW_INFERENCE_PRIVATE.json').read_text())
   if permit['expires_epoch']-time.time()<1200:lease(f'lease_batch{offset:04d}')
   records=list(pool.map(run_one,range(offset,min(offset+8,350))))
   commit(records);progress('reference_leg_running')
 result=progress('reference_leg_finished' if not STOP.is_set() and len(list(R.glob('*/EXECUTION_PRIVATE.json')))==350 else 'reference_leg_stopped_preserved')
 save(HERE/'KIMI_FINAL_PUBLIC.json',result)
 gateway_info=json.loads((W/'GATEWAY_PUBLIC.json').read_text());os.kill(gateway_info['pid'],15)
 print(json.dumps(result),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  progress('reference_leg_control_failed_preserve_no_retry');print(json.dumps({'fatal_error_type':type(e).__name__,'private_error_preserved':True}),flush=True);raise SystemExit(2)
