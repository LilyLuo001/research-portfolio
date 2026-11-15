"""Exact public-file publication; no research rows, input bundles or ARM controls."""
import hashlib,json,os
from pathlib import Path
S=Path(__file__).parent;repo=Path(os.environ['LINKUP_REPO']);B=repo/'linkup/reuse_first_20261115';prefix='execution_20261116/continuation01/'
reports=['STARTING_QUALIFICATION_STATUS_PUBLIC.json','RESUME_INVENTORY_PUBLIC.json','CREATED_JOIN_PUBLIC.json','FAILED_OUTPUT_REUSE_PUBLIC.json','INITIAL_OUTPUT_REUSE_PUBLIC.json','REFERENCE_PREFLIGHT_INITIAL_FAILURE_PUBLIC.json','REFERENCE_PREFLIGHT_PUBLIC.json','GAP_REGISTER_PUBLIC.json','LATEST_QUALIFICATION_STATUS_PUBLIC.json','CHECKPOINT_PUBLIC.json','CHECKPOINT_TRANSPORT_RECOVERY_PUBLIC.json','FINAL_INTEGRITY_PUBLIC.json','CANDIDATE_FAILURE_DIAGNOSTIC_PUBLIC.json','EXECUTION_STATUS_PUBLIC.json','CONTINUATION_NOTE_ZH.md']
codes=sorted(p.name for p in S.glob('*.py') if p.name.startswith(('cloud_','preflight001_','test_')) or p.name in ['qualification_metrics.py','publish_continuation.py'])
allow=json.loads((B/'PUBLIC_GIT_ALLOWLIST.json').read_text());manifest=json.loads((B/'PUBLIC_COPY_MANIFEST.json').read_text());added=[]
def clean(x):
 if isinstance(x,str):
  for src,dst in [(str(repo)+'/','repository:'),(str(S.parent)+'/','external_public:'),(str(Path('/home')/'linkup'/'migration')+'/','azure_workspace:')]:x=x.replace(src,dst)
  return x
 if isinstance(x,list):return [clean(v) for v in x]
 if isinstance(x,dict):return {clean(k):clean(v) for k,v in x.items()}
 return x
for name in reports+codes:
 raw=(S/name).read_bytes();dest=prefix+('code/' if name in codes else '')+name;data=(json.dumps(clean(json.loads(raw)),ensure_ascii=False,indent=2)+'\n').encode() if name.endswith('.json') else raw
 p=B/dest;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);added.append(dest)
 manifest['copies']=[x for x in manifest['copies'] if x['published_file']!=dest]
 manifest['copies'].append({'source_label':'external_public:execution_20261116_continuation01/'+name,'source_sha256':hashlib.sha256(raw).hexdigest(),'published_file':dest,'published_sha256':hashlib.sha256(data).hexdigest(),'source_modified':False,'transform':'Public JSON artifact paths aliased; source code and notes byte-identical. Private records and controls excluded.'})
allow['allowed_files']=sorted(set(allow['allowed_files']+added));(B/'PUBLIC_GIT_ALLOWLIST.json').write_text(json.dumps(allow,indent=2)+'\n');(B/'PUBLIC_COPY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'public_files':len(added),'private_data_files_copied':0,'git_staging_performed':False}))
