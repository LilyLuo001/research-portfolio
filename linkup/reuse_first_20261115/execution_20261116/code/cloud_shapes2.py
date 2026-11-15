from pathlib import Path
import json,zlib,base64,importlib.util
R=Path.home()/'migration';O=R/'execution_20261116/run001'
r=json.loads((O/'stage1/MANIFEST_CONTENT_READ_PUBLIC.json').read_text());out={'patterns':r['shape_patterns'],'runtime':{x:importlib.util.find_spec(x) is not None for x in ['tiktoken','jsonschema','pyarrow','pandas']}}
s=json.loads((R/'astra/extraction/STATE_PRIVATE.json').read_text());out['astra_entry_shape']={k:type(v).__name__ for k,v in next(iter(s['accepted'].values())).items()}
b=json.loads((R/'opencode_kimi_20261115/run01/bulk_1309_20261115/CANDIDATE_STATE_PRIVATE.json').read_text());one=next(iter(b['engineering_candidates'].values()));p=Path(one['path']);out['candidate_parent_filenames']=[x.name for x in p.parent.iterdir() if x.is_file()][:20]
e=base64.b64encode(zlib.compress(json.dumps(out).encode(),9)).decode();assert len(e)<3800,len(e);print(json.dumps({'aggregate_zlib_b64':e}))
