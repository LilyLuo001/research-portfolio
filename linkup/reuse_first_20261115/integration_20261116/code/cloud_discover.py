"""Bounded metadata discovery on the existing Azure VM; no source-body/model reads."""
import base64, datetime, hashlib, json, os, re, sqlite3, sys, urllib.parse, zlib
from pathlib import Path

R = Path.home() / 'migration'
O = R / 'integration_20261116/run001'
O.mkdir(parents=True, exist_ok=True, mode=0o700)
sys.path.insert(0, str(R / 'code'))
from workflow import call

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_bytes())
def blocked(s): return 'batch035' in s.lower() or '01a17beb-973b-74e2-adbb-20f8d004b1fc' in s.lower()
def shape(v):
    if isinstance(v, dict): return {str(k): ('dict:' + ','.join(list(x)[:20]) if isinstance(x,dict) else 'list:' + str(len(x)) if isinstance(x,list) else type(x).__name__) for k,x in list(v.items())[:35]}
    if isinstance(v,list): return {'type':'list','length':len(v),'first_shape':shape(v[0]) if v else None}
    return type(v).__name__

files = {}
for rel in ['AZURE_RESEARCH_IDENTITIES_PRIVATE.json','AZURE_PRO_BATCH_METADATA_PUBLIC.json','AZURE_FIXED10K_IDENTITY_PRIVATE.json','astra/extraction/STATE_PRIVATE.json','opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json','opencode_kimi_20261115/run01/bulk_1309_20261115/EXCEPTION_RECORDS_PRIVATE.json','kimi_assessment_20261110/queue_count_v1/CONTEXT_INDEX_PRIVATE.json']:
    p=R/rel
    if not p.exists(): files[rel]={'exists':False}; continue
    assert p.stat().st_size < 16*1024*1024
    b=p.read_bytes(); v=json.loads(b)
    files[rel]={'exists':True,'sha256':sha(b),'size':len(b),'shape':shape(v)}
    if isinstance(v,dict):
        files[rel]['container_shapes']={k:shape(x[:1] if isinstance(x,list) else {a:x[a] for a in list(x)[:1]}) for k,x in v.items() if isinstance(x,(list,dict)) and k in ['accepted','engineering_candidates','exceptions','handled','rows']}

wanted_shas = ['794d76b2a6e913d7d08adab7e99bc96a3f57f8553c73518ae27b966a8fad86fb','355e4ee49d35d4974a4fe3af4027136303116e578a4ef2a6e29bf3f9deb8e612','641f2d3204a8f65f2483be485815ede04b57920227af4b867afd41cbd6de62b6','9ea1fcd0f61182d2d125b19d90af820f549e77351ff1064320613c311ae0d8a9']
inventory=[]
for cluster in ['kunshan','wuzhen','huazhong']:
    db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    sql="SELECT path,root,rel,size,status,sha FROM files WHERE (path LIKE '%corpus_pro_review_20261026%' AND (rel LIKE '%PACKET_MANIFEST_PRIVATE.jsonl' OR rel LIKE '%CHECKPOINT_RECEIPT_PUBLIC.json' OR rel LIKE '%MERGED_RECEIPT_PUBLIC.json' OR rel LIKE '%PACKET_PREPARATION_PUBLIC.json' OR rel LIKE '%REUSE_AD_BINDINGS_PRIVATE.jsonl')) OR sha IN (?,?,?,?)"
    for path,root,rel,size,status,digest in db.execute(sql,wanted_shas):
        if blocked(path): continue
        inventory.append(dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=digest))
    db.close()
(O/'DISCOVERY_PRIVATE.json').write_text(json.dumps({'metadata_inventory':inventory,'local_files':files},indent=2)+'\n')
os.chmod(O/'DISCOVERY_PRIVATE.json',0o600)

def fetch(meta, range_only=False):
    assert meta['status']=='verified' and not blocked(meta['path'])
    cfg=read(R/'private'/(meta['cluster']+'.json'))
    url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(meta['root']).name+'/'+meta['rel'],safe='/')
    headers={'x-ms-version':'2023-11-03'}
    if range_only: headers['Range']='bytes=0-65535'
    with call(url,'https://storage.azure.com/',headers=headers) as response: b=response.read(65537 if range_only else meta['size']+1)
    if not range_only: assert len(b)==meta['size'] and sha(b)==meta['sha256']
    return b

probes={}
for suffix in ['PACKET_MANIFEST_PRIVATE.jsonl','CHECKPOINT_RECEIPT_PUBLIC.json','MERGED_RECEIPT_PUBLIC.json','PACKET_PREPARATION_PUBLIC.json']:
    choices=sorted([x for x in inventory if x['rel'].endswith(suffix) and x['status']=='verified' and x['size']<2000000],key=lambda x:x['path'])
    if not choices: continue
    m=choices[-1];b=fetch(m);v=json.loads(b.splitlines()[0]) if suffix.endswith('jsonl') else json.loads(b)
    probes[suffix]={'size':len(b),'sha256':sha(b),'shape':shape(v)}
    if suffix.endswith('RECEIPT_PUBLIC.json'):
        probes[suffix]['counts']=v.get('counts');probes[suffix]['packet_shape']=shape(v.get('packets',[{}])[0]) if v.get('packets') else None
for digest in wanted_shas:
    choices=[x for x in inventory if x['sha256']==digest and x['status']=='verified']
    if not choices: probes[digest]={'found':False};continue
    m=choices[0];b=fetch(m,True)
    try:v=json.loads(b.splitlines()[0]);s=shape(v)
    except (json.JSONDecodeError,UnicodeDecodeError):s='first_line_not_complete_json'
    probes[digest]={'found':True,'size':m['size'],'shape':s,'schema_probe_only_not_verified_full_download':True}

macro={}
for name in ['EXECUTION_RECEIPT_PUBLIC.json','QA_PUBLIC.json','FINAL_VERIFICATION_PUBLIC.json','ANNUAL_US_2016_2026.json','MONTHLY_US_2016_2026.json','PREPOST_CHANGE_PUBLIC.json','ANNUAL_OCCUPATION_COMPOSITION.json']:
    p=R/'macro_records_20261115/run004'/name
    if p.exists():
        b=p.read_bytes();macro[name]={'size':len(b),'sha256':sha(b),'shape':shape(json.loads(b))}
running=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        b=p.read_bytes()
        for name in ['cloud_benchmark_worker.py','bulk_worker.py']:
            if name.encode() in b and int(p.parent.name)!=os.getpid():running.append({'pid':int(p.parent.name),'known_script':name})
    except (OSError,ValueError): pass
report={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'known_worker_matches':running,'metadata_files_discovered':len(inventory),'distinct_transferred_content_sha':len({x['sha256'] for x in inventory}),'inventory_total_bytes':sum({x['sha256']:x['size'] for x in inventory}.values()),'schema_probes':probes,'local_file_shapes':files,'macro':macro,'source_bodies_or_model_calls':0}
(O/'DISCOVERY_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(report).encode())).decode()}))
