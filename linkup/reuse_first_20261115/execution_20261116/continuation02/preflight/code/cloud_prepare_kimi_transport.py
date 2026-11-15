"""Transport only: fixed 350 blind reference inputs; no candidate answers or calls."""
import base64,datetime,gzip,hashlib,json,os,subprocess,sys,zlib
from pathlib import Path
os.umask(0o077)
R=Path.home()/'migration';Q=R/'execution_20261116/run001/qualification500_v1';D=Q/'kimi_reference350_v1';P=Q/'reference_preflight002';L=Q/'luna_revision002'
D.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def immutable(p,b):
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
assert sha(P/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl')=='19ed3c19fbffe976acc77e894222072b0d93b23d4c6c517a7ec79c2d29b6883d'
rows=[json.loads(x) for x in (P/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl').read_text().splitlines()]
assert len(rows)==350 and len({x['case'] for x in rows})==350
assert len({x['row']['context_sha256'] for x in rows})==350
sys.path.insert(0,str(R/'code'));import validate_reviews
validate_reviews.validate_packet([x['row'] for x in rows])
pins={'code/validate_reviews.py':'f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20','astra/extraction/FORMAL800_REVIEW_SCHEMA.json':'fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e','astra/extraction/REVIEW_INSTRUCTIONS.md':'f13e1c431b4018fb7d1e2f1dc985dece69f092a8713c7ef673497a0fbd728d26'}
for rel,h in pins.items():assert sha(R/rel)==h
bundle={'items':rows,'schema':read(R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json'),'schema_text':(R/'astra/extraction/FORMAL800_REVIEW_SCHEMA.json').read_text(),'instructions':(R/'astra/extraction/REVIEW_INSTRUCTIONS.md').read_text(),'pins':pins,'exclusions_snapshot':read(L/'EXCLUSIONS_PRIVATE.json'),'source_inputs_sha256':sha(P/'BLIND_NEW_REFERENCE_INPUTS_PRIVATE.jsonl')}
raw=gzip.compress(json.dumps(bundle,ensure_ascii=False,separators=(',',':')).encode(),mtime=0)
p=D/'INPUT_BUNDLE_PRIVATE.json.gz';immutable(p,raw)
from checkpoint_scope import upload,BASE
from workflow import token
key='reuse-execution/20261116/run001/qualification500_v1/kimi_reference350_v1/INPUT_BUNDLE_PRIVATE.json.gz'
receipt=upload(p,key)
pub=D/'TRANSFER_PUBLIC.pem';immutable(pub,TRANSFER_PUBLIC_KEY.encode())
compressed=zlib.compress(token('https://storage.azure.com/').encode());encrypted=[]
for offset in range(0,len(compressed),400):
    e=subprocess.run(['openssl','pkeyutl','-encrypt','-pubin','-inkey',str(pub),'-pkeyopt','rsa_padding_mode:oaep','-pkeyopt','rsa_oaep_md:sha256'],input=compressed[offset:offset+400],capture_output=True,check=True)
    encrypted.append(base64.b64encode(e.stdout).decode())
report={'status':'fixed_blind350_prepared_no_inference','inputs':350,'source_url':BASE+key,'source_bytes':len(raw),'source_sha256':receipt['sha256'],'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_answers_read':0,'model_calls':0}
(D/'TRANSPORT_PREPARE_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
answer={'report':report,'encrypted_storage_token':encrypted}
assert len(json.dumps(answer))<3800
print(json.dumps(answer))

