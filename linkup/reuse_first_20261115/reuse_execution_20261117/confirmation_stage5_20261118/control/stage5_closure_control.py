"""Publish aggregate outcome on the existing VM after checking this run is terminal."""
import base64
import hashlib
import json
from pathlib import Path
import time
import zlib

D = Path(__file__).resolve().parents[1]


def dispatch(action, control, base):
    assert action == 'close_stage5'
    names = ['STAGE5_OUTCOME_PUBLIC.json', 'STAGE5_RESULT_ZH.md']
    files = {name: {'b64z': base64.b64encode(zlib.compress((D/name).read_bytes(), 9)).decode(),
                    'sha256': hashlib.sha256((D/name).read_bytes()).hexdigest()} for name in names}
    source = base + '\nFILES=' + repr(files) + r'''
import base64,zlib
outcome=json.loads(zlib.decompress(base64.b64decode(FILES['STAGE5_OUTCOME_PUBLIC.json']['b64z'])))
S=C/'scoring_v1'
assert sha(S/'SCORING_PUBLIC.json')==outcome['sources_sha256']['SCORING_PUBLIC.json']
assert sha(S/'ASTRA_DIAGNOSTIC_PUBLIC.json')==outcome['sources_sha256']['ASTRA_DIAGNOSTIC_PUBLIC.json']
assert not read(S/'SCORING_PUBLIC.json')['eligible_measure_dependencies']
locations={'Luna':C/'luna','Kimi':C/'kimi_direct_v4','Astra':C/'astra_diagnostic_v1'}
for leg,directory in locations.items():
    final=read(directory/(leg.upper()+'_FINAL_PUBLIC.json'))
    assert final['terminal_no_active_requests']
    assert sha(directory/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256']
    for key in ('physical_attempts','logical_calls','reserved_usd','input_tokens','output_tokens','output_sha256'):
        assert final[key]==outcome['model_legs'][leg][key]
active=0
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:args=path.read_bytes().split(b'\0')
    except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    worker=any(x.endswith((b'/stage5_cloud_worker.py',b'/stage5_kimi_worker.py')) for x in args)
    if worker and any(str(p).encode() in args for p in locations.values()):active+=1
assert active==0,'stage5_worker_still_active'
for name,value in FILES.items():
    raw=zlib.decompress(base64.b64decode(value['b64z']));assert hashlib.sha256(raw).hexdigest()==value['sha256']
    path=S/name
    if path.exists():assert path.read_bytes()==raw,'immutable_outcome_conflict'
    else:
        with path.open('xb') as file:file.write(raw)
    assert sha(path)==value['sha256']
print(json.dumps({'status':'stage5_outcome_saved_verified_no_pilot','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'directory':str(S),'files_sha256':{k:v['sha256'] for k,v in FILES.items()},'active_stage5_workers':active,
    'eligible_measure_count':0,'new_model_calls':0,'pilot_launched':False,'Astra_judgments_received':0,
    'conservative_reserved_usd':outcome['budget']['conservative_reserved_usd']}))
'''
    compile(source, '<stage5-closure>', 'exec')
    result = control.vm(source, 'stage5_closure_' + str(time.time_ns()))
    control.save(D/'control/STAGE5_CLOSURE_PUBLIC.json', result)
    print(json.dumps(result))
