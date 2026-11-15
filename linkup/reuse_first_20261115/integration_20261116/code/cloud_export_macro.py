"""Verify and export existing public macro series; no raw data rescan or new estimation."""
import json,hashlib,base64,zlib,datetime
from pathlib import Path
R=Path.home()/'migration';S=R/'macro_records_20261115/run004';O=R/'integration_20261116/run001'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((S/'EXECUTION_RECEIPT_PUBLIC.json').read_text());pins={Path(x['path']).name:x for x in receipt['outputs']}
sources={}
for name in ['MONTHLY_US_2016_2026.json','ANNUAL_US_2016_2026.json','PREPOST_CHANGE_PUBLIC.json','QA_PUBLIC.json']:
 p=S/name;assert p.stat().st_size==pins[name]['bytes'] and sha(p)==pins[name]['sha256'];sources[name]=sha(p)
m=json.loads((S/'MONTHLY_US_2016_2026.json').read_text())['rows'];a=json.loads((S/'ANNUAL_US_2016_2026.json').read_text())['rows'];p=json.loads((S/'PREPOST_CHANGE_PUBLIC.json').read_text())
assert len(m)==129 and len(a)==11
for r in a:assert sum(x['first_observed_records'] for x in m if x['month'].startswith(str(r['year'])))==r['first_observed_records_available']
d={'status':'existing_macro_series_exported_no_reestimation','observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'notice':'CREATED is first-observed proxy; descriptive changes are not AI causal effects.','monthly_columns':['month','first_observed_advertisements','active_missing_delete_open','partial_boundary_month'],'monthly_rows':[[x['month'],x['first_observed_records'],x['active_missing_delete_open'],x['partial_boundary_month']] for x in m],'annual_columns':['year','first_observed_available','first_observed_complete_months','complete_months'],'annual_rows':[[x['year'],x['first_observed_records_available'],x['first_observed_records_complete_months'],x['complete_months']] for x in a],'source_sha256':sources,'new_model_calls':0,'new_original_ad_reads':0}
q=O/'PAPER_MACRO_SERIES_PUBLIC.json';q.write_text(json.dumps(d,indent=2)+'\n')
b=base64.b64encode(zlib.compress(json.dumps(d,separators=(',',':')).encode(),9)).decode();assert len(b)<3800
print(json.dumps({'aggregate_zlib_b64':b,'report_sha256':sha(q)}))
