"""Once-terminal scoring and bounded diagnostics; never changes frozen gates."""
import base64,hashlib,json,time,zlib
from pathlib import Path
D=Path(__file__).resolve().parents[1]
def score(control,base):
 names=('cloud_score_adapter.py','astra_diagnostic_compare.py','README.md','test_field_score.py')
 frozen_path=D/'protocol/PROTOCOL_FREEZE.json';frozen=json.loads(frozen_path.read_text())
 frozen_sha=hashlib.sha256(frozen_path.read_bytes()).hexdigest()
 for name in ('README.md','test_field_score.py'):
  assert hashlib.sha256((D/'protocol'/name).read_bytes()).hexdigest()==frozen['files'][name],'local_frozen_companion_mismatch'
 files={n:{'b64z':base64.b64encode(zlib.compress((D/'protocol'/n).read_bytes(),9)).decode(),'sha256':hashlib.sha256((D/'protocol'/n).read_bytes()).hexdigest()} for n in names}
 source=base+'\nFILES='+repr(files)+'\nFROZEN_BUNDLE_SHA='+repr(frozen_sha)+'''
import base64,zlib,urllib.error
os.umask(0o077);K=C/'kimi_direct_v4';V=C/'runtime_direct_v4';P=C/'protocol';S=C/'scoring_v1';L=C/'luna'
final=read(K/'KIMI_FINAL_PUBLIC.json');assert final['terminal_no_active_requests'] and final['outputs_accounted']==135
assert sha(K/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256'];S.mkdir(exist_ok=True)
assert sha(P/'PROTOCOL_FREEZE.json')==FROZEN_BUNDLE_SHA,'existing_protocol_freeze_mismatch'
frozen=read(P/'PROTOCOL_FREEZE.json')
for name,x in FILES.items():
 raw=zlib.decompress(base64.b64decode(x['b64z']));assert hashlib.sha256(raw).hexdigest()==x['sha256'];p=P/name
 if name in ('README.md','test_field_score.py'):assert x['sha256']==frozen['files'][name],'frozen_companion_hash_mismatch'
 if p.exists():assert p.read_bytes()==raw,'immutable_protocol_or_adapter_conflict'
 else:p.write_bytes(raw)
for name,digest in frozen['files'].items():assert sha(P/name)==digest,'frozen_protocol_member_mismatch'
assert sha(P/'field_score.py')=='2c37e739154296ea969da4126fe92bc922a8d1e5c07c4a42bcca505e9caa5ae0'
repo=C/'repo';fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py';ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
def run(cmd,name):
 cp=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 (S/(name+'_EXECUTION_PRIVATE.json')).write_text(json.dumps({'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr}))
 assert cp.returncode==0,name+'_failed_private_details_retained'
 return json.loads(cp.stdout) if cp.stdout.strip() else {}
if not (K/'VALIDATION_PUBLIC.json').exists():
 r=run([sys.executable,'-B',str(V/'stage5_validate_kimi.py'),'--directory',str(K),'--transport-outputs',str(K/'OUTPUTS_PRIVATE.jsonl'),'--validated-outputs',str(K/'VALIDATED_OUTPUTS_PRIVATE.jsonl'),'--field-validator',str(fv),'--frozen-validator',str(ov)],'KIMI_VALIDATION')
 (K/'VALIDATION_PUBLIC.json').write_text(json.dumps(r,sort_keys=True)+'\\n')
common=['--frame',str(C/'FRAME_PRIVATE.jsonl'),'--frame-freeze',str(C/'FRAME_FREEZE_PUBLIC.json')]
exclusions=[str(L/'EXCLUSIONS_EXPORT_PRIVATE.json'),str(K/'EXCLUSIONS_EXPORT_PRIVATE.json')]
if not (S/'JOIN_PUBLIC.json').exists():
 run([sys.executable,'-B',str(P/'cloud_score_adapter.py'),'join',*common,'--inputs',str(K/'INPUTS_PRIVATE.jsonl'),'--luna-outputs',str(L/'OUTPUTS_PRIVATE.jsonl'),'--luna-final',str(L/'LUNA_FINAL_PUBLIC.json'),'--kimi-outputs',str(K/'VALIDATED_OUTPUTS_PRIVATE.jsonl'),'--kimi-final',str(K/'KIMI_FINAL_PUBLIC.json'),'--kimi-validation-receipt',str(K/'VALIDATION_PUBLIC.json'),'--exclusions',*exclusions,'--repo',str(repo),'--output-directory',str(S)],'JOIN')
if not (S/'SCORES_PRIVATE.json').exists():
 cmd=read(S/'SCORING_COMMAND_PUBLIC.json')['argv'];assert Path(cmd[1]).resolve()==(P/'field_score.py').resolve();cmd.insert(1,'-B');run(cmd,'FROZEN_PRIMARY_SCORE')
if not (S/'SCORING_PUBLIC.json').exists():
 run([sys.executable,'-B',str(P/'cloud_score_adapter.py'),'report',*common,'--scores',str(S/'SCORES_PRIVATE.json'),'--inputs',str(K/'INPUTS_PRIVATE.jsonl'),'--exclusions',*exclusions,'--output-directory',str(S)],'REPORT')
public=read(S/'SCORING_PUBLIC.json');assert public['primary_gate_unchanged'] and not public['primary_reference_overwritten']
transport=S/'SCORING_TRANSPORT_PUBLIC.json'
if transport.exists():print(json.dumps(read(transport)))
else:
 sys.path.insert(0,str(R/'code'));from workflow import call
 key='review-delivery/stage5/20261118/SCORING_PUBLIC.json';url='https://stlinkup70d455c0261104.blob.core.windows.net/astra-handoff/'+key;raw=(S/'SCORING_PUBLIC.json').read_bytes()
 try:
  with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:assert response.read(1000001)==raw,'public_blob_conflict'
 except urllib.error.HTTPError as exc:
  if exc.code!=404:raise
  with call(url,'https://storage.azure.com/',method='PUT',body=raw,headers={'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'}) as response:assert response.status==201
 with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:assert response.read(1000001)==raw
 r={'status':'frozen_primary_scored_public_summary_verified','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'blob_key':key,'astra_source_only_requests':public['astra_source_only_requests'],'new_model_calls':0,'reference_overwritten':False,'primary_gate_unchanged':True}
 transport.write_text(json.dumps(r,sort_keys=True)+'\\n');print(json.dumps(r))
'''
 compile(source,'<stage5-frozen-scoring>','exec');r=control.vm(source,'stage5_score_direct_'+str(time.time_ns()));control.save(D/'control/SCORING_TRANSPORT_PUBLIC.json',r);print(json.dumps(r))
def download(control,base):
 import sys
 sys.path.insert(0,str(D.parent/'continuation_dispatch_20261117'));import storage_transport as storage
 t=json.loads((D/'control/SCORING_TRANSPORT_PUBLIC.json').read_text())
 with storage.call(storage.HOST+'/'+storage.CONTAINER+'/'+t['blob_key'],storage.storage_token()) as response:raw=response.read(1000001)
 assert len(raw)==t['bytes'] and hashlib.sha256(raw).hexdigest()==t['sha256']
 p=D/'SCORING_PUBLIC.json'
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
 x=json.loads(raw);print(json.dumps({'status':'scoring_public_summary_download_verified','accounting':x['accounting'],'production_admission':x['production_admission'],'astra_source_only_requests':x['astra_source_only_requests']}))
def dispatch(action,control,base):
 return {'score_direct_kimi':score,'download_scoring':download}[action](control,base)
