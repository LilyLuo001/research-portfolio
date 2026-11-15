"""Bounded source/exception metadata probe for unresolved reuse and identity joins."""
import collections,datetime,hashlib,importlib.util,json,os,re,sqlite3,sys
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';O=B/'continuation01';O.mkdir(exist_ok=True);os.umask(0o077)
read=lambda p:json.loads(p.read_bytes())
idx=sqlite3.connect((R/'integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
db=sqlite3.connect((B/'stage2/revision003/REUSED_VALUES_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
states=dict(idx.execute('select h,state from final_status'));got={h for h, in db.execute('select distinct h from document')};missing={h:s for h,s in states.items() if h not in got};ident=read(R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json')['rows'];tasks={x['context_sha256']:x['task'] for x in ident};ks=read(R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json');saved=[]
for h,s in missing.items():
    if s!='saved_unverified':continue
    t=tasks.get(h);e=ks.get('exceptions',{}).get(t,{})
    saved.append({'context_sha256':h,'task':t,'exception':e,'handled':ks.get('handled',{}).get(t,{}),'events':[{'asset':a,'state':st,'source':sr,'detail':de} for a,st,sr,de in idx.execute('select asset,state,source,detail from event where h=?',(h,))]})
accepted=[];ig=R/'integration_20261116/run001';report=read(ig/'revision003/INTEGRATION_PUBLIC.json')
for g in report['metadata_gaps']:
    receipt=read(ig/'metadata_cache'/(g['receipt_sha256']+'.metadata'))
    for p in receipt['packets']:
        d=p.get('validated_sha256')
        if p['status']=='accepted' and d and not (ig/'revision003/packet_metadata'/(d+'.metadata')).exists():accepted.append({'checkpoint_sha256':g['receipt_sha256'],'packet':p,'checkpoint_inputs':receipt.get('inputs'), 'checkpoint_outputs':receipt.get('outputs')})
unreconciled=collections.Counter()
for h,s in states.items():
    if s=='not_reconciled':
        for a,st,de in idx.execute('select asset,state,detail from event where h=?',(h,)):unreconciled[a,st,de]+=1
metadata=[];lookup_digests={x['packet']['validated_sha256'] for x in accepted}
for cluster in ['kunshan','wuzhen','huazhong']:
    c=sqlite3.connect((R/cluster/'LEDGER_PRIVATE.sqlite').as_uri()+'?mode=ro',uri=True)
    for path,root,rel,size,status,d in c.execute("select path,root,rel,size,status,sha from files where path like '%metadata_research_20261026%' or path like '%linkup_metadata_research_20261026%' or sha in ("+','.join('?' for _ in lookup_digests)+')',list(lookup_digests)):
        if 'batch035' not in path.lower():metadata.append({'cluster':cluster,'path':path,'root':root,'rel':rel,'size':size,'status':status,'sha256':d})
    c.close()
mapping=read(B/'stage2/REMAINING_SOURCE_LOCATORS_PRIVATE.json')['mapping'];shards=set()
for m in read(ig/'DISCOVERY_PRIVATE.json')['metadata_inventory']:
    if m['rel'].endswith('PACKET_MANIFEST_PRIVATE.jsonl'):
        p=ig/'metadata_cache'/(m['sha256']+'.metadata')
        if p.exists():
            for l in p.open():
                row=json.loads(l)
                if states.get(row['context_sha256'])=='accepted_original_scope':shards.add(row['shard_id'])
catalog=[json.loads(l) for l in (R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl').open()]
selected_catalog=[x for x in catalog if x['shard_id'] in shards]
private={'missing_saved_cases':saved,'missing_accepted_packets':accepted,'metadata_locators':metadata,'selected_Pro_shard_catalog':selected_catalog}
(O/'RESUME_LOCATORS_PRIVATE.json').write_text(json.dumps(private,indent=2)+'\n')
sys.path.insert(0,str(R/'macro_records_20261115/dependencies'))
try:
    import duckdb;runtime={'duckdb':duckdb.__version__,'available':True}
except ImportError:runtime={'available':False}
counts=collections.Counter((x['exception'].get('status'),x['handled'].get('status'),bool(x['task']),bool(x['exception'].get('retry_forbidden'))) for x in saved)
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'missing_saved_total':len(saved),'missing_saved_by_exception':[{'exception_status':a,'handled_status':b,'has_task':t,'retry_forbidden':f,'n':n} for (a,b,t,f),n in counts.items()],'missing_saved_exception_field_names':sorted(set(k for x in saved for k in x['exception'])),'missing_accepted_packets':len(accepted),'missing_accepted_packet_field_names':sorted(set(k for x in accepted for k in x['packet'])),'missing_accepted_SHA_found_in_migration':sum(x['sha256'] in lookup_digests for x in metadata),'unreconciled_event_states':[{'asset':a,'state':s,'batch_or_reason':d,'n':n} for (a,s,d),n in unreconciled.items()],'metadata_research_files':len(metadata),'metadata_basenames':sorted(set(Path(x['rel']).name for x in metadata)),'selected_Pro_base_shards':len(selected_catalog),'selected_Pro_base_catalog_field_names':sorted(selected_catalog[0]) if selected_catalog else [],'existing_SQL_runtime':runtime,'new_model_calls':0,'raw_description_files_read':0}
(O/'RESUME_INVENTORY_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
import base64,zlib
enc=base64.b64encode(zlib.compress(json.dumps(report).encode(),9)).decode();assert len(enc)<3800;print(json.dumps({'aggregate_zlib_b64':enc}))
