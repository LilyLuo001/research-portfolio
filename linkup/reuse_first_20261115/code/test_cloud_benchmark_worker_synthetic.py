"""Offline synthetic execution tests. No model, VM, identity or network calls."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch


HERE=Path(__file__).absolute().parent
WORKER=HERE/'cloud_benchmark_worker.py'
CONFIG=HERE.parent/'BENCHMARK_CONFIG_PUBLIC.json'


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj))


def fixture(home):
    root=home/'migration';dest=root/'reuse_first_20261115/run01/benchmark20'
    dest.mkdir(parents=True)
    config=json.loads(CONFIG.read_text());write(dest/'BENCHMARK_CONFIG_PUBLIC.json',config)
    (dest/'SCHEMA.json').write_text('{}')
    (dest/'INSTRUCTIONS.md').write_text('Synthetic test fixture only.')
    rows=[]
    for n in range(20):
        text=f'Synthetic document number {n}. No real advertisement.'
        rows.append({'task':f'synthetic/case{n}', 'row':{'record_id':f'fixture{n}','context_sha256':hashlib.sha256(text.encode()).hexdigest(),'full_document':text}})
    (dest/'INPUTS_PRIVATE.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    write(dest/'EXCLUSIONS_PRIVATE.json',{'tasks':[]})
    runtime=root/'code/validate_reviews.py';runtime.parent.mkdir(parents=True);runtime.write_text('# Synthetic validator stand-in; never executed.\n')
    write(dest/'WORKER_INPUT_PINS_PUBLIC.json',{'files':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ['INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','BENCHMARK_CONFIG_PUBLIC.json']},'runtime':{'code/validate_reviews.py':hashlib.sha256(runtime.read_bytes()).hexdigest()}})
    write(root/'astra/extraction/STATE_PRIVATE.json',{'unchanged':True})
    write(root/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json',{'unchanged':True})
    return root,dest,config


class Clock:
    def __init__(self):self.value=2000000000.
    def time(self):return self.value
    def sleep(self,seconds):self.value+=seconds


class Response:
    def __init__(self,status,body,headers=None):
        self.status=status;self.body=body;self.headers=headers or {};self.closed=False
    def read(self,n):return self.body[:n]
    def close(self):self.closed=True


def execute(home,mode='success',auth_failure=False):
    module=types.ModuleType('synthetic_worker')
    exec(compile(WORKER.read_text(),str(WORKER),'exec'),module.__dict__)
    clock=Clock();calls=[];responses=[];auth_resources=[]
    identity=types.ModuleType('workflow')
    def token(resource):
        auth_resources.append(resource)
        if auth_failure:raise RuntimeError('synthetic identity failure')
        return 'synthetic'+'-authentication-value'
    identity.token=token
    def request(req,timeout):
        body=json.loads(req.data);user=json.loads(body['messages'][1]['content'])
        calls.append({'record':user['record_id'],'epoch':clock.time(),'timeout':timeout})
        index=len(calls)
        if mode=='transport' and index==1:raise TimeoutError('synthetic ambiguous outcome')
        if mode=='retries' and index%2==1:
            response=Response(429,b'{"error":"synthetic throttle"}',{'retry-after-ms':'1'})
        elif mode=='filter' and index==1:
            response=Response(403,b'{"error":{"code":"content_filter"}}')
        elif mode=='invalid' and index==1:
            response=Response(200,b'not a JSON response')
        else:
            message={'content':'{}'}
            if mode=='refusal' and index==1:message['refusal']='Synthetic refusal marker.'
            response=Response(200,json.dumps({'model':'synthetic-model','choices':[{'finish_reason':'stop','message':message}],'usage':{'prompt_tokens':11,'completion_tokens':7,'total_tokens':18}}).encode(),{'x-ratelimit-limit-tokens':'100000'})
        responses.append(response);return response
    opener=types.SimpleNamespace(open=request)
    def validate(args,**kwargs):
        receipt=Path(args[args.index('--public-receipt')+1]);write(receipt,{'status':'pass'})
        return types.SimpleNamespace(returncode=0)
    old_path=sys.path[:];old_umask=os.umask(0o077)
    try:
        with patch.object(module.Path,'home',return_value=home),patch.object(module,'time',clock),patch.dict(sys.modules,{'workflow':identity}),patch.object(module.urllib.request,'build_opener',return_value=opener),patch.object(module.urllib.request,'urlopen',side_effect=AssertionError('network forbidden')),patch.object(module.subprocess,'run',side_effect=validate):
            module.main()
    finally:
        sys.path[:]=old_path;os.umask(old_umask)
    assert all(response.closed for response in responses)
    assert all(resource=='https://cognitiveservices.azure.com/' for resource in auth_resources)
    return calls


def check_accounting(dest,config):
    state=json.loads((dest/'RUN_STATUS_PUBLIC.json').read_text())
    events={}
    log=dest/'ATTEMPTS_PRIVATE.jsonl'
    if log.exists():
        for line in log.read_text().splitlines():
            e=json.loads(line);events[e['ordinal'],e['attempt']]=e
    assert len(events)<=config['max_physical_attempts']
    assert sum(e['reservation_usd'] for e in events.values())<=config['run_reservation_cap_usd']
    for event in events.values():
        used=sum(e['token_reservation'] for e in events.values() if 0<=event['forwarded_epoch']-e['forwarded_epoch']<60)
        assert used<=config['scheduled_tpm_ceiling']
    assert state['new_production_accepted']==0 and state['no_human_gold_claim']
    assert state['original_ledgers_unchanged']
    return state


def main():
    checks=[]
    for mode in ['success','retries','filter','refusal','transport','invalid']:
        with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
            home=Path(tmp);root,dest,config=fixture(home);calls=execute(home,mode)
            state=check_accounting(dest,config)
            assert len(calls)==(24 if mode=='retries' else 20)
            if mode=='success':assert state['engineering_pass']==20
            if mode in ('filter','refusal'):
                assert 'synthetic/case0' in json.loads((dest/'EXCLUSIONS_PRIVATE.json').read_text())['tasks']
            if mode in ('filter','refusal','invalid'):
                assert (dest/'results/case0000/HTTP_RESPONSE_attempt01_PRIVATE.bin').exists()
            assert not execute(home),'Completed/failed cases must not be sent again on restart'
            check_accounting(dest,config);checks.append(mode+'_and_restart_no_duplicate')
    with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
        home=Path(tmp);root,dest,config=fixture(home)
        assert execute(home,auth_failure=True)==[]
        state=check_accounting(dest,config)
        assert state['status']=='authentication_or_authorization_failed'
        assert state['physical_attempts']==0
        checks.append('identity_failure_zero_model_calls')
    with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
        home=Path(tmp);root,dest,config=fixture(home)
        event={'ordinal':0,'attempt':1,'forwarded_epoch':1999999900.,'status':'forwarding_uncertain','reservation_usd':.001,'token_reservation':1}
        (dest/'ATTEMPTS_PRIVATE.jsonl').write_text(json.dumps(event)+'\n')
        calls=execute(home)
        assert len(calls)==19 and all(c['record']!='fixture0' for c in calls)
        check_accounting(dest,config);checks.append('interrupted_attempt_not_resubmitted')
    with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
        home=Path(tmp);root,dest,config=fixture(home)
        write(dest/'EXCLUSIONS_PRIVATE.json',{'tasks':['synthetic/case0']})
        calls=execute(home)
        assert len(calls)==19 and all(c['record']!='fixture0' for c in calls)
        check_accounting(dest,config);checks.append('existing_protected_task_never_forwarded')
    with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
        home=Path(tmp);root,dest,config=fixture(home)
        event={'ordinal':0,'attempt':1,'forwarded_epoch':1999999900.,'status':'forwarding_uncertain','reservation_usd':.9999,'token_reservation':1}
        (dest/'ATTEMPTS_PRIVATE.jsonl').write_text(json.dumps(event)+'\n')
        assert execute(home)==[]
        check_accounting(dest,config);checks.append('persisted_cost_reservation_blocks_new_calls')
    with tempfile.TemporaryDirectory(prefix='linkup-synthetic-') as tmp:
        home=Path(tmp);root,dest,config=fixture(home)
        (root/'code/validate_reviews.py').write_text('# changed synthetic runtime\n')
        try:execute(home)
        except AssertionError as error:assert str(error)=='runtime_pin_changed'
        else:raise AssertionError('Runtime mismatch must stop before requests')
        assert not (dest/'ATTEMPTS_PRIVATE.jsonl').exists()
        checks.append('runtime_hash_mismatch_zero_calls')
    print(json.dumps({'status':'pass','scenario_count':len(checks),'scenarios':checks,'real_model_calls':0,'VM_calls':0,'real_identity_calls':0,'raw_source_records_read':0}))


if __name__=='__main__':main()
