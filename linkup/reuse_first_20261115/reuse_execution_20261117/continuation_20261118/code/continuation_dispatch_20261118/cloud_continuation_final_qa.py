"""Final read-only output SHA, bijection and run-state check."""
import os,json,hashlib,datetime
from pathlib import Path
R=Path.home()/'migration';S=R/'source_binding_20261118/run002';p=S/'DESCRIPTION_TO_BASE_SOURCE_BINDING_PUBLIC.json';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='3ea31864e6b0e64a763a360aa461b775d6ef4f6246f0c0c9f74fa9930cb54906';r=json.loads(b);f=next(x for x in r['outputs'] if x['file'].endswith('.jsonl'));data=(S/f['file']).read_bytes();assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest()==f['sha256'];rows=[json.loads(l) for l in data.splitlines()];assert len(rows)==2464;assert all(x['status']=='source_provenance_bound' for x in rows);assert len({x['shard_id'] for x in rows})==2464;assert len({x['provider']['provider_manifest_entry_identity'] for x in rows})==2464
E=R/'evidence_readiness_20261117/run002';e=json.loads((E/'EVIDENCE_READINESS_PUBLIC.json').read_text());q=json.loads((E/'PREFIX_QA_PUBLIC.json').read_text());assert e['remaining_allowed_evidence_atoms']==0 and e['new_production_accepted']==0;assert q['old_rows_compared_all_columns']==126000 and q['new_rows_strictly_after_old_cursor']==54888
known=['cloud_evidence_readiness.py','cloud_evidence_resume.py','cloud_bind_description_sources','cloud_small_data_stats.py','cloud_evidence_prefix_qa.py','cloud_qualification_luna_worker','cloud_astra_audit_worker','opencode_kimi'];processes=[]
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  data=p.read_bytes();labels=[s for s in known if s.encode() in data]
  if labels and int(p.parent.name)!=os.getpid():processes.append({'pid':int(p.parent.name),'labels':labels})
 except (OSError,ValueError):pass
out={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'source_crosswalk_SHA_bijection_and_evidence_conservation_verified','provider_to_base_rows':2464,'unique_base_shards':2464,'unique_provider_entries':2464,'crosswalk_sha256':f['sha256'],'evidence_atoms_checked':180888,'previous_rows_exactly_preserved':126000,'newly_checked_evidence_atoms':54888,'related_running_processes':processes,'new_model_calls':0,'new_semantic_acceptances':0,'timers_resumed':False,'new_resources_created':False,'global_ad_identity_join_complete':False,'all_field_gaps_complete':False,'phase_budget_cap_usd_unchanged':450}
O=R/'continuation_control_20261118';p=O/'CONTINUATION_FINAL_QA_PUBLIC.json'
with p.open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out))
