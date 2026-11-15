"""Metadata-only locator probe; never model-submit missing or failed contexts."""
import json,collections,datetime,hashlib,sqlite3,os
from pathlib import Path
R=Path.home()/'migration';B=R/'execution_20261116/run001';C=B/'continuation01';os.umask(0o077)
def read(p):return json.loads(p.read_bytes())
left=read(C/'joined_revision002/REMAINING_SAVED_LOCATORS_PRIVATE.json'); report={'remaining_saved_event_summary':[{'has_task':bool(x['task']),'task':x['task'],'events':x['events']} for x in left]}
report['run01_files']=[str(p.relative_to(R)) for p in (R/'opencode_kimi_20261115/run01').glob('*') if p.is_file()]
report['run01_result_directories']=[str(p.relative_to(R)) for p in (R/'opencode_kimi_20261115/run01/results').glob('*') if p.is_dir()]
report['missing_accepted_packets']=read(C/'RESUME_LOCATORS_PRIVATE.json')['missing_accepted_packets']
report['astra_state_keys']=list(read(R/'astra/extraction/STATE_PRIVATE.json'))
# Do not read provider-restricted content; only known metadata records for these bounded gaps.
(C/'REMAINING_LOCATOR_PROBE_PRIVATE.json').write_text(json.dumps(report,indent=2)+'\n')
safe={'remaining_tasks':[x['task'] for x in left], 'remaining_events':[{'asset':e['asset'],'state':e['state'],'detail':e['detail']} for x in left for e in x['events']], 'run01_files':report['run01_files'],'run01_result_directories':report['run01_result_directories'],'accepted_packet_names':[x['packet']['name'] for x in report['missing_accepted_packets']],'accepted_checkpoint_input_keys':[list(x.get('checkpoint_inputs') or {}) for x in report['missing_accepted_packets']],'accepted_checkpoint_output_keys':[list(x.get('checkpoint_outputs') or {}) for x in report['missing_accepted_packets']],'astra_state_keys':report['astra_state_keys']}
import base64,zlib
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(safe).encode(),9)).decode()}))
