"""Bounded private metadata lookup for initial candidates and two missing accepted packets."""
import collections,datetime,hashlib,json,os,sqlite3,sys,urllib.parse
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';D=C/'remaining_probe';D.mkdir(exist_ok=False);os.umask(0o077)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
statepath=R/'opencode_kimi_20261115/run01/CANDIDATE_STATE_PRIVATE.json';state=read(statepath);report={'initial_state_keys':list(state),'initial_state_shape':{k:{'type':type(v).__name__,'n':len(v) if isinstance(v,(list,dict)) else None,'entry_keys':sorted({kk for e in (v.values() if isinstance(v,dict) else v if isinstance(v,list) else []) if isinstance(e,dict) for kk in e})} for k,v in state.items()},'initial_final_keys':list(read(R/'opencode_kimi_20261115/run01/FINAL_VERIFICATION_PUBLIC.json'))}
paths=[]
for i in range(5):
 d=R/'opencode_kimi_20261115/run01/results'/f'{i:03d}'
 paths.append({'directory':str(d),'files':[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in d.iterdir() if p.is_file()]})
(D/'INITIAL_PATHS_PRIVATE.json').write_text(json.dumps(paths,indent=2)+'\n');report['initial_file_names']=sorted({x['name'] for p in paths for x in p['files']})
loc=read(C/'RESUME_LOCATORS_PRIVATE.json');need={d for x in loc['missing_accepted_packets'] for d in (x.get('checkpoint_outputs') or {}).values() if isinstance(d,str) and len(d)==64};found={};configs={}
for cluster in ['kunshan','wuzhen','huazhong']:
 c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
 for path,root,rel,size,status,h in c.execute('select path,root,rel,size,status,sha from files where sha in ('+','.join('?' for _ in need)+')',list(need)):
  if status=='verified' and 'batch035' not in path.lower():found.setdefault(h,{'cluster':cluster,'root':root,'rel':rel,'size':size})
 c.close();configs[cluster]=read(R/'private'/(cluster+'.json'))
assert sum(x['size'] for x in found.values())<64000000
sys.path.insert(0,str(R/'code'));from workflow import call
cached=[]
for h,x in found.items():
 cfg=configs[x['cluster']];url=cfg['container_sas'].split('?',1)[0]+'/'+urllib.parse.quote(cfg['snapshot']+'/'+Path(x['root']).name+'/'+x['rel'],safe='/')
 with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as r:data=r.read(x['size']+1)
 assert len(data)==x['size'] and hashlib.sha256(data).hexdigest()==h;p=D/(h+'.data');p.write_bytes(data);lines=data.splitlines();shape={}
 if lines:
  try:row=json.loads(lines[0]);shape={'type':type(row).__name__,'keys':list(row) if isinstance(row,dict) else None}
  except (ValueError,UnicodeError):shape={'not_jsonl_first_line':True}
 cached.append({'sha256':h,'bytes':len(data),'rows_or_lines':len(lines),'shape':shape})
report['accepted_aggregate_outputs_requested']=len(need);report['accepted_aggregate_outputs_found']=cached
# Existing Astra failed result metadata only; no external model request.
report['astra_top_dirs']=[str(p.relative_to(R)) for p in (R/'astra/extraction').iterdir() if p.is_dir()]
(D/'ACCEPTED_AGGREGATE_LOCATORS_PRIVATE.json').write_text(json.dumps(found,indent=2)+'\n')
(D/'PROBE_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
import base64,zlib
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(report).encode(),9)).decode()}))
