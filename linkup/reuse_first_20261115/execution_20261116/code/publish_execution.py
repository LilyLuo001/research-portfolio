"""Publish an exact list of public aggregates and code; never copy raw controls/data."""
import hashlib,json,os
from pathlib import Path
src=Path(__file__).parent;repo=Path(os.environ['LINKUP_REPO']);base=repo/'linkup/reuse_first_20261115';prefix='execution_20261116/'
reports=['EXECUTION_AUTHORIZATION_PUBLIC.json','MANIFEST_CONTENT_READ_COMPACT_PUBLIC.json','SCOPE_RECONCILIATION_PUBLIC.json','ALL_SHARD_ACCOUNTING_PUBLIC.json','RECORDS_SOURCE_DEDUP_PUBLIC.json','VALUES_ATTACHMENT_PUBLIC.json','REMAINING_DISCOVERY_PUBLIC.json','SAVED_OUTPUT_VERIFICATION_PUBLIC.json','REUSE_CLOSURE_PUBLIC.json','GAP_REGISTER_PUBLIC.json','FIELD_COVERAGE_REGISTER_PUBLIC.json','QUALIFICATION_DRAFT_REJECTION_PUBLIC.json','QUALIFICATION_FRAME_PUBLIC.json','QUALIFICATION_INPUT_PREPARATION_PUBLIC.json','QUALIFICATION_PROTOCOL_V1_PUBLIC.json','QUALIFICATION_LUNA_CONFIG_PUBLIC.json','QUALIFICATION_LAUNCH_PUBLIC.json','WORKER_SYNTHETIC_TEST_PUBLIC.json','PUBLIC_ACCOUNTING_CHECKS_PUBLIC.json','EXECUTION_CHECKPOINT_PUBLIC.json','PACKAGING_FAULT_STOP_PUBLIC.json','REAL_PACKET_CONTRACT_TEST_PUBLIC.json','WORKER_V2_SYNTHETIC_TEST_PUBLIC.json','PACKAGING_REPAIR_RESUME_PUBLIC.json','PACKAGING_REPAIR_CHECKPOINT_PUBLIC.json','LATEST_QUALIFICATION_STATUS_PUBLIC.json','EXECUTION_STATE_PUBLIC.json','EXECUTION_NOTE_ZH.md','SYNTHETIC_CONFIG_PUBLIC.json']
codes=sorted(p.name for p in src.glob('*.py') if p.name.startswith(('cloud_','test_')))+['publish_execution.py']
allow=json.loads((base/'PUBLIC_GIT_ALLOWLIST.json').read_text());manifest=json.loads((base/'PUBLIC_COPY_MANIFEST.json').read_text());new=[]
def clean(x):
    if isinstance(x,str):
        for a,b in [(str(repo)+'/','repository:'),(str(src.parent)+'/','external_public:'),('/home/linkup/migration/','azure_workspace:')]:x=x.replace(a,b)
        return x
    if isinstance(x,list):return [clean(v) for v in x]
    if isinstance(x,dict):return {clean(k):clean(v) for k,v in x.items()}
    return x
for name in reports+codes:
    raw=(src/name).read_bytes();rel=prefix+('code/' if name in codes else '')+name
    if name.endswith('.json'):data=(json.dumps(clean(json.loads(raw)),ensure_ascii=False,indent=2)+'\n').encode()
    else:data=raw
    dst=base/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);new.append(rel)
    manifest['copies']=[m for m in manifest['copies'] if m['published_file']!=rel]
    manifest['copies'].append({'source_label':'external_public:execution_20261116/'+name,'source_sha256':hashlib.sha256(raw).hexdigest(),'published_file':rel,'published_sha256':hashlib.sha256(data).hexdigest(),'source_modified':False,'transform':'Public JSON machine-specific artifact paths aliased; code/Markdown byte-identical. No private inputs, responses, IDs or credential-bearing ARM receipts copied.'})
allow['allowed_files']=sorted(set(allow['allowed_files']+new));(base/'PUBLIC_GIT_ALLOWLIST.json').write_text(json.dumps(allow,indent=2)+'\n');(base/'PUBLIC_COPY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'public_files_copied':len(new),'private_raw_or_control_files_copied':False,'git_staging_performed':False}))
