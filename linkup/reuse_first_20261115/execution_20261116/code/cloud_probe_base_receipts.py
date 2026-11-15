import json,sqlite3,hashlib,urllib.parse,sys,base64,zlib
from pathlib import Path
R=Path.home()/'migration';O=R/'execution_20261116/run001/stage1';cat=R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl';sample=[json.loads(l) for _,l in zip(range(3),cat.open())];needed={x['original_receipt_sha256'] for x in sample};found={}
for cluster in ['kunshan','wuzhen','huazhong']:
 c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for path,root,rel,size,status,h in c.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in needed)+')',list(needed)):
  if status=='verified':found.setdefault(h,dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=h))
 c.close()
sys.path.insert(0,str(R/'code'));from workflow import call
out=[]
for h,m in found.items():
 cfg=json.loads((R/'private'/(m['cluster']+'.json')).read_text());url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
 assert m['size']<2*1024*1024
 with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as res:b=res.read(m['size']+1)
 assert hashlib.sha256(b).hexdigest()==h
 (O/'metadata_cache'/(h+'.metadata')).write_bytes(b);j=json.loads(b)
 out.append({'sha256':h,'shape':{k:(list(v) if isinstance(v,dict) else type(v).__name__) for k,v in j.items()},'numeric_fields':{k:v for k,v in j.items() if isinstance(v,(int,float)) and not isinstance(v,bool)},'nested_numeric_fields':{k:{kk:vv for kk,vv in v.items() if isinstance(vv,(int,float)) and not isinstance(vv,bool)} for k,v in j.items() if isinstance(v,dict)}})
(O/'BASE_RECEIPT_PROBE_PUBLIC.json').write_text(json.dumps(out,indent=2)+'\n');e=base64.b64encode(zlib.compress(json.dumps(out).encode(),9)).decode();assert len(e)<3800;print(json.dumps({'aggregate_zlib_b64':e}))
