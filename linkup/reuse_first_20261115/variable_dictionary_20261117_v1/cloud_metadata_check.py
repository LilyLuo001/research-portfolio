"""Read only control metadata and database schema; no raw records or inference."""
from pathlib import Path
import json, hashlib, datetime, sqlite3, os, base64, zlib
os.umask(0o077)
r=Path.home()/'migration'
paths={'state':'execution_20261116/run001/AZURE_RESEARCH_STATE.json','gap':'execution_20261116/run001/continuation02/final_checkpoint/GAP_REGISTER_PUBLIC.json','field_coverage':'execution_20261116/run001/FIELD_COVERAGE_REGISTER_PUBLIC.json','shadow':'measurement_protocol_20261117/shadow001/SHADOW_DIAGNOSTIC_PUBLIC.json'}
files={}
for key,rel in paths.items():
 p=r/rel
 files[key]={'relative_to_migration':rel,'exists':p.is_file()}
 if p.is_file():files[key].update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
state=json.loads((r/paths['state']).read_text())
gap=json.loads((r/paths['gap']).read_text())
dbpath=r/state['database_relative_to_migration']
assert dbpath.resolve().is_relative_to(r.resolve())
schema={}
with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
 db.execute('PRAGMA query_only=ON')
 for name in ['document','ad','accepted_original_values','saved_unverified_values','metadata_resolution','accepted_values_with_created']:
  schema[name]=[{'name':row[1],'type':row[2]} for row in db.execute('PRAGMA table_info('+name+')')]
report={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'variable_dictionary_current_metadata_preflight','files':files,'current_state':{k:state.get(k) for k in ['status','new_authorized_cap_usd','stage3_cap_usd','step4_released','step6_released','whole_delivery_unique_missing_field_inputs','new_production_accepted']},'scope_units':gap['scope_units'],'fine_semantic_states':gap['fine_semantic_states'],'db_schema_only':schema,'db_row_values_read':0,'raw_advertisement_files_read':0,'model_calls':0,'production_jobs_started':0}
o=r/'variable_dictionary_20261117_v1';o.mkdir(exist_ok=True)
p=o/'CLOUD_METADATA_CHECK_PUBLIC.json'
assert not p.exists(),'immutable_receipt_exists'
b=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode();p.write_bytes(b)
payload=json.dumps({'sha256':hashlib.sha256(b).hexdigest(),'zlib_b64':base64.b64encode(zlib.compress(b,9)).decode()})
assert len(payload)<3800
print(payload)
