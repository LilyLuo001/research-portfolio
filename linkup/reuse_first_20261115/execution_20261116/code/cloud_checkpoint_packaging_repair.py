"""Archive the bounded packaging repair and already-returned responses, not live outputs."""
import base64,datetime,hashlib,json,os,sys,tarfile
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';Q=B/'qualification500_v1';D=Q/'luna_revision002'
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
os.umask(0o077)
code=B/'repair_code';code.mkdir(exist_ok=False)
for name,encoded in FILES_B64.items():(code/name).write_bytes(base64.b64decode(encoded))
selected=[Q/'PACKAGING_FAULT_STOP_PUBLIC.json',B/'AZURE_RESEARCH_STATE.json']+list(code.iterdir())
selected += [D/n for n in ['PACKAGING_REPAIR_PUBLIC.json','RESUME_PUBLIC.json','REUSED_RESPONSE_MAP_PRIVATE.json','INPUTS_PRIVATE.jsonl','SCHEMA.json','INSTRUCTIONS.md','PROTOCOL_PUBLIC.json','BENCHMARK_CONFIG_PUBLIC.json','WORKER_INPUT_PINS_PUBLIC.json','cloud_qualification_luna_worker.py','REAL_PACKET_CONTRACT_TEST_PUBLIC.json','WORKER_V2_SYNTHETIC_TEST_PUBLIC.json','ORIGINAL_LEDGER_PINS_PUBLIC.json']]
for x in read(D/'REUSED_RESPONSE_MAP_PRIVATE.json'):
    selected += [p for p in (D/'results'/x['case']).iterdir() if p.is_file()]
pins={p.relative_to(B).as_posix():sha(p) for p in selected}
(Q/'PACKAGING_REPAIR_FILES_PRIVATE.json').write_text(json.dumps(pins,indent=2)+'\n');selected.append(Q/'PACKAGING_REPAIR_FILES_PRIVATE.json')
archive=B/'QUALIFICATION_PACKAGING_REPAIR_PRIVATE.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for p in selected:tar.add(p,arcname=p.relative_to(B).as_posix(),recursive=False)
assert all(sha(B/rel)==h for rel,h in pins.items())
sys.path.insert(0,str(R/'code'));from checkpoint_scope import upload,BASE;from workflow import call
key='reuse-execution/20261116/run001/QUALIFICATION_PACKAGING_REPAIR_PRIVATE.tar.gz';upload(archive,key)
digest=hashlib.sha256();n=0
with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
    while True:
        data=response.read(1048576)
        if not data:break
        n+=len(data);digest.update(data)
assert n==archive.stat().st_size and digest.hexdigest()==sha(archive)
status=read(D/'RUN_STATUS_PUBLIC.json')
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'packaging_repair_checkpoint_readback_verified','archive_blob_key':key,'archive_bytes':n,'archive_sha256':digest.hexdigest(),'full_readback_SHA_verified':True,'original_reuse_checkpoint_retained':True,'model_requests_by_checkpoint':0,'reused_old_calls':10,'same_model_messages_and_500_contexts':True,'old_failure_revision_retained':True,'latest_qualification_status':status,'new_production_accepted':0,'paper_paused':True}
(B/'PACKAGING_REPAIR_CHECKPOINT_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
