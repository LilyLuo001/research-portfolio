"""Publish explicit sanitized files only; preserve preflight snapshots and source pins."""
import hashlib,json,os,sys
from pathlib import Path
S=Path(__file__).parent;repo=Path(os.environ['LINKUP_REPO']);B=repo/'linkup/reuse_first_20261115';stage=sys.argv[1]
assert stage in ('preflight','final')
selection=json.loads((S/(stage.upper()+'_PUBLIC_FILES.json')).read_text());prefix='execution_20261116/continuation02/'+stage+'/'
allow=json.loads((B/'PUBLIC_GIT_ALLOWLIST.json').read_text());manifest=json.loads((B/'PUBLIC_COPY_MANIFEST.json').read_text());added=[]
def clean(x):
 if isinstance(x,str):
  for a,b in [(str(repo)+'/','repository:'),(str(S.parent)+'/','external_public:'),(str(Path('/home')/'linkup'/'migration')+'/','azure_workspace:')]:x=x.replace(a,b)
  return x
 if isinstance(x,list):return [clean(v) for v in x]
 if isinstance(x,dict):return {clean(k):clean(v) for k,v in x.items()}
 return x
for name in selection:
 assert '/' not in name and not name.endswith('PRIVATE.json')
 raw=(S/name).read_bytes();dest=prefix+('code/' if name.endswith('.py') else '')+name
 data=(json.dumps(clean(json.loads(raw)),ensure_ascii=False,indent=2)+'\n').encode() if name.endswith('.json') else raw
 p=B/dest;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data,'published_snapshot_cannot_change'
 else:p.write_bytes(data)
 added.append(dest);manifest['copies']=[x for x in manifest['copies'] if x['published_file']!=dest]
 manifest['copies'].append({'source_label':'external_public:execution_20261116_continuation02/'+name,'source_sha256':hashlib.sha256(raw).hexdigest(),'published_file':dest,'published_sha256':hashlib.sha256(data).hexdigest(),'source_modified':False,'transform':'Exact allowlist; public JSON paths aliased. Source and notes byte-identical. No private records, requests, controls, output labels or credentials.'})
allow['allowed_files']=sorted(set(allow['allowed_files']+added));(B/'PUBLIC_GIT_ALLOWLIST.json').write_text(json.dumps(allow,indent=2)+'\n');(B/'PUBLIC_COPY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(S/(stage.upper()+'_PUBLISHED_PATHS.json')).write_text(json.dumps(added,indent=2)+'\n');print(json.dumps({'public_files':len(added),'private_data_files_copied':0,'git_staging_performed':False}))
