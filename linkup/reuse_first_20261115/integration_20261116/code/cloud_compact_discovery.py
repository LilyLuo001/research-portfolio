import base64,json,zlib,os
from pathlib import Path
p=Path.home()/'migration/integration_20261116/run001'
a=json.loads((p/'DISCOVERY_PUBLIC.json').read_text())
# Shape inspection may contain dynamic map keys: keep original only as private.
(p/'DISCOVERY_RAW_PRIVATE.json').write_text(json.dumps(a));os.chmod(p/'DISCOVERY_RAW_PRIVATE.json',0o600)
r={k:a[k] for k in ['observed_at_utc','metadata_files_discovered','distinct_transferred_content_sha','inventory_total_bytes','schema_probes','known_worker_matches']}
r['local_schemas']={name:{'top_keys':list(v.get('shape',{})), 'container_value_schemas':{k:list(c.values()) if isinstance(c,dict) else type(c).__name__ for k,c in v.get('container_shapes',{}).items()}} for name,v in a['local_file_shapes'].items()}
(p/'DISCOVERY_PUBLIC.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'aggregate_zlib_b64':base64.b64encode(zlib.compress(json.dumps(r).encode())).decode()}))
