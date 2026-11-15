"""Read only previously located delivery manifests; no raw data scan or model calls."""
import json,os,hashlib,datetime,collections,base64,zlib,concurrent.futures,urllib.parse,sys,csv,io,time,fcntl
from pathlib import Path
R=Path.home()/'migration';O=R/'execution_20261116/run001/stage1';os.umask(0o077);O.mkdir(parents=True,exist_ok=True);cache=O/'metadata_cache';cache.mkdir(exist_ok=True)
f=(O/'STAGE1.lock').open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
sys.path.insert(0,str(R/'code'));from workflow import call
p=R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CATALOG_LOCATORS_AND_MANIFEST_CANDIDATES_PRIVATE.json';old=json.loads(p.read_bytes());items=[]
for cluster,v in old['clusters'].items():items+=v['delivery_manifest_name_candidates']
unique={m['sha256']:m for m in items if m['status']=='verified' and 'batch035' not in m['path'].lower()};assert len(unique)<=600 and sum(m['size'] for m in unique.values())<16*1024*1024
configs={k:json.loads((R/'private'/(k+'.json')).read_bytes()) for k in ['kunshan','wuzhen','huazhong']}
t0=time.monotonic()
def sh(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def fetch(dm):
 d,m=dm;p=cache/(d+'.metadata')
 try:
  if p.exists():assert p.stat().st_size==m['size'] and sh(p)==d;return d,None,0
  c=configs[m['cluster']];url=c['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(c['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
  with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:b=r.read(m['size']+1)
  assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==d
  with p.open('xb') as w:w.write(b)
  return d,None,len(b)
 except Exception as e:return d,{'exception_type':type(e).__name__,'http_status':getattr(e,'code',None)},0
errors=[];verified=[];newbytes=0
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for d,e,n in pool.map(fetch,unique.items()):
  if e:errors.append({'sha256':d,**e})
  else:verified.append(d);newbytes+=n
patterns={};private=[]
def sig(v):
 if isinstance(v,dict):return {k:('dict:'+','.join(list(x)[:20]) if isinstance(x,dict) else 'list:'+str(len(x))+(':'+','.join(list(x[0])[:15]) if x and isinstance(x[0],dict) else '') if isinstance(x,list) else type(x).__name__) for k,x in v.items()}
 if isinstance(v,list):return {'type':'list','length':len(v),'first_keys':list(v[0]) if v and isinstance(v[0],dict) else None}
 return {'type':type(v).__name__}
for d in verified:
 m=unique[d];data=(cache/(d+'.metadata')).read_bytes();o=None;parse=None
 try:o=json.loads(data);parse='json'
 except Exception:
  try:o=list(csv.DictReader(io.StringIO(data.decode()),delimiter='\t' if Path(m['rel']).suffix=='.tsv' else ','));parse='tabular_metadata'
  except Exception:parse='unparsed_metadata'
 s=sig(o);key=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
 if key not in patterns:patterns[key]={'count':0,'basename':Path(m['rel']).name,'shape':s,'sample_source_sha256':d}
 patterns[key]['count']+=1
 # Numeric metadata only, no body content; preserve source-specific values privately.
 private.append({'sha256':d,'locator':m,'format':parse,'shape_signature':key})
(O/'VERIFIED_DELIVERY_METADATA_PRIVATE.json').write_text(json.dumps(private,indent=2)+'\n')
summary={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'manifest_content_download_verified_scope_interpretation_in_progress','metadata_locations':len(items),'unique_verified_metadata_contents':len(verified),'bytes_downloaded':newbytes,'files_sha_verified':len(verified),'failures':errors,'shape_patterns':list(patterns.values()),'source_advertisement_files_read':0,'model_calls':0,'step1_infrastructure_risk_allowance_usd':25,'new_resources':0,'elapsed_seconds':time.monotonic()-t0,'exact_full_delivery_unique_ads':None}
(O/'MANIFEST_CONTENT_READ_PUBLIC.json').write_text(json.dumps(summary,indent=2)+'\n')
small={k:v for k,v in summary.items() if k not in ['shape_patterns','failures']};small['errors']=len(errors);small['distinct_shape_patterns']=len(patterns);small['report_sha256']=sh(O/'MANIFEST_CONTENT_READ_PUBLIC.json')
print(json.dumps(small))
