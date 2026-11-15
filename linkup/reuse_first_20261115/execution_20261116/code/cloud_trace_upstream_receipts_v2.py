import json,sqlite3,hashlib,urllib.parse,sys,base64,zlib,collections
from pathlib import Path
R=Path.home()/'migration';O=R/'execution_20261116/run001/stage1';cache=O/'metadata_cache';initial=json.loads((O/'BASE_RECEIPT_PROBE_PUBLIC.json').read_text());current=[x['sha256'] for x in initial];report=[];private=[]
sys.path.insert(0,str(R/'code'));from workflow import call
for depth in range(4):
 wanted=set()
 for d in current:
  p=cache/(d+'.metadata')
  if not p.exists():continue
  x=json.loads(p.read_bytes())
  for k in ['source_receipt_sha256','input_receipt_sha256','source_manifest_sha256','shard_complete_sha256']:
   if isinstance(x.get(k),str):wanted.add(x[k])
 if not wanted:break
 found={}
 for cluster in ['kunshan','wuzhen','huazhong']:
  db=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
  for path,root,rel,size,status,h in db.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in wanted)+')',list(wanted)):
   if status=='verified':found.setdefault(h,dict(cluster=cluster,path=path,root=root,rel=rel,size=size,status=status,sha256=h))
  db.close()
 current=[]
 for h,m in found.items():
  assert m['size']<2*1024*1024
  p=cache/(h+'.metadata')
  if not p.exists():
   cfg=json.loads((R/'private'/(m['cluster']+'.json')).read_text());url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(m['root']).name+'/'+m['rel'],safe='/')
   with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as q:b=q.read(m['size']+1)
   assert len(b)==m['size'] and hashlib.sha256(b).hexdigest()==h;p.write_bytes(b)
  x=json.loads(p.read_bytes());current.append(h);private.append(m)
  report.append({'depth':depth+1,'sha256':h,'basename':Path(m['rel']).name,'keys':list(x),'numeric':{k:v for k,v in x.items() if isinstance(v,(int,float)) and not isinstance(v,bool)},'nested_numeric':{k:{kk:vv for kk,vv in v.items() if isinstance(vv,(int,float)) and not isinstance(vv,bool)} for k,v in x.items() if isinstance(v,dict)}})
(cache.parent/'UPSTREAM_PROBE_LOCATORS_PRIVATE.json').write_text(json.dumps(private,indent=2)+'\n');(O/'UPSTREAM_RECEIPT_PROBE_V2_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n');summary=[{k:v for k,v in x.items() if k not in ['sha256','basename']} for x in report];e=base64.b64encode(zlib.compress(json.dumps(summary).encode(),9)).decode();assert len(e)<3800,len(e);print(json.dumps({'aggregate_zlib_b64':e}))
