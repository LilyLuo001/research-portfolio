from pathlib import Path
import json,base64,zlib
p=Path.home()/'migration/integration_20261116/run001'
a=json.loads((p/'DISCOVERY_RAW_PRIVATE.json').read_text())
r={'files':a['metadata_files_discovered'],'distinct_sha':a['distinct_transferred_content_sha'],'total_bytes':a['inventory_total_bytes'],'probes':a['schema_probes']}
r['local']={}
for name in ['astra/extraction/STATE_PRIVATE.json','opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json','opencode_kimi_20261115/run01/bulk_1309_20261115/EXCEPTION_RECORDS_PRIVATE.json']:
 v=a['local_file_shapes'][name];r['local'][Path(name).name]={'top_keys':list(v.get('shape',{})),'containers':{k:list(c.values()) if isinstance(c,dict) else type(c).__name__ for k,c in v.get('container_shapes',{}).items()}}
encoded=base64.b64encode(zlib.compress(json.dumps(r).encode())).decode()
assert len(encoded)<3800, len(encoded)
print(json.dumps({'aggregate_zlib_b64':encoded}))
