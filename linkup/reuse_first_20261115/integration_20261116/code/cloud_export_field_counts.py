"""Export already computed aggregate field-state counts, never row identifiers."""
import json,base64,zlib,hashlib
from pathlib import Path
p=Path.home()/'migration/integration_20261116/run001/revision003'
a=json.loads((p/'INTEGRATION_PUBLIC.json').read_text())
r={'status':'existing_index_field_status_counts_exported','source_report_sha256':hashlib.sha256((p/'INTEGRATION_PUBLIC.json').read_bytes()).hexdigest(),'units':{'fixed10k':'original ad-by-field-family rows, 10000 ads per family','Pro':'unique accepted context-by-outcome dimension, 31690 projected of31700 accepted contexts','Pro_merged':'overlapping audited reference subset; do not add to Pro totals'},'field_status_counts':a['field_status_counts'],'known_accepted_Pro_contexts_missing_status_projection':10,'unknown_and_partial_are_not_negatives':True,'new_model_calls':0}
q=p/'FIELD_STATUS_COUNTS_PUBLIC.json';q.write_text(json.dumps(r,indent=2)+'\n')
b=base64.b64encode(zlib.compress(json.dumps(r).encode(),9)).decode();assert len(b)<3700
print(json.dumps({'aggregate_zlib_b64':b,'report_sha256':hashlib.sha256(q.read_bytes()).hexdigest()}))
