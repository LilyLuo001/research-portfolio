"""Bounded Astra controls. Import/build is offline; dispatch is explicit.

Astra reads only the frozen scorer's source-only subset and never changes the
Kimi primary score. A durable launch intent forbids automatic resubmission even
if a controller dies between spawning the worker and recording its PID.
"""
import hashlib
import json
from pathlib import Path
import time

D = Path(__file__).resolve().parents[1]
BLOB_KEY = 'review-delivery/stage5/20261118/ASTRA_DIAGNOSTIC_PUBLIC.json'
PINNED_FILES = tuple('runtime/' + name for name in (
    'stage5_common.py', 'stage5_cloud_worker.py', 'stage5_kimi_gateway.py',
    'stage5_kimi_worker.py', 'stage5_prepare.py', 'stage5_validate_kimi.py')) + tuple(
    'protocol/' + name for name in ('cloud_score_adapter.py', 'astra_diagnostic_compare.py',
                                  'field_score.py', 'CONFIRMATION_PROTOCOL.json', 'PROTOCOL_FREEZE.json'))

# Used both before upload and after download; only this aggregate schema may cross
# the private Blob output transport. Case/source identifiers are not permitted.
PUBLIC_VALIDATION = r'''
def validate_diagnostic(x, measure_ids):
    import math, re
    expected = {'status', 'frame_count', 'diagnostics_selected', 'source_only_requests',
        'late_blocked_metadata_only', 'physical_attempts', 'reserved_usd', 'measure_diagnostics',
        'original_primary_scores_sha256', 'astra_outputs_sha256', 'reference_overwritten',
        'primary_gates_recomputed', 'production_admission', 'new_model_calls_by_diagnostic_tool',
        'interpretation'}
    assert set(x) == expected, 'diagnostic_public_schema_changed'
    assert x['status'] == 'bounded_astra_diagnostics_only' and x['frame_count'] == 135
    for key in ('reference_overwritten', 'primary_gates_recomputed', 'production_admission'):
        assert x[key] is False, 'diagnostic_must_not_change_primary_or_admit_production'
    assert type(x['new_model_calls_by_diagnostic_tool']) is int and x['new_model_calls_by_diagnostic_tool'] == 0
    for key in ('diagnostics_selected', 'source_only_requests'):
        assert type(x[key]) is int and 1 <= x[key] <= 6
    assert x['source_only_requests'] <= x['diagnostics_selected']
    for key in ('late_blocked_metadata_only', 'physical_attempts'):
        assert type(x[key]) is int and 0 <= x[key] <= 6
    assert x['late_blocked_metadata_only'] <= x['source_only_requests']
    assert type(x['reserved_usd']) in (float, int) and math.isfinite(x['reserved_usd']) and 0 <= x['reserved_usd'] <= 8
    for key in ('original_primary_scores_sha256', 'astra_outputs_sha256'):
        assert re.fullmatch('[a-f0-9]{64}', x[key])
    assert x['interpretation'] == 'Third-machine agreement diagnostics; no gold labels or new qualification.'
    assert set(x['measure_diagnostics']) == set(measure_ids)
    counters = {'blocked_metadata_only', 'primary_packet_unavailable', 'audited_slots',
        'astra_luna_comparable', 'astra_luna_agreement', 'astra_kimi_comparable', 'astra_kimi_agreement',
        'not_comparable_all_three', 'astra_agrees_with_both', 'astra_agrees_with_luna_only',
        'astra_agrees_with_kimi_only', 'astra_agrees_with_neither'}
    for values in x['measure_diagnostics'].values():
        assert set(values) <= counters
        assert all(type(v) is int and 0 <= v <= x['source_only_requests'] for v in values.values())
    return x
def parse_diagnostic(raw):
    def pairs(items):
        result={}
        for key,value in items:
            assert key not in result, 'duplicate_diagnostic_key'
            result[key]=value
        return result
    return json.loads(raw, object_pairs_hook=pairs)
'''
exec(PUBLIC_VALIDATION)

COMMON = r'''
import contextlib, fcntl, math
os.umask(0o077)
K=C/'kimi_direct_v4'; S=C/'scoring_v1'; A=C/'astra_diagnostic_v1'
V=C/'runtime'; P=C/'protocol'; L=C/'luna'
PREPARE=C/'ASTRA_PREPARE_PUBLIC.json'; BINDING=C/'ASTRA_PREPARE_BINDING_PRIVATE.json'
LAUNCH=C/'ASTRA_LAUNCH_PUBLIC.json'; INTENT=C/'ASTRA_LAUNCH_INTENT_PRIVATE.json'
TRANSPORT=S/'ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json'
HOLD_STATES={'forwarding_uncertain', 'transport_uncertain_no_retry', 'usage_reservation_breach_stop',
             'returned_model_identity_mismatch_hold'}
KNOWN_STATES=HOLD_STATES | {'response_saved', 'retryable_confirmed_http', 'terminal_http_error',
    'quarantined_provider_filter_or_refusal', 'response_saved_identity_resolved_prior'}
def emit(value):
    raw=json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    assert len(raw.encode()) < 4096, 'aggregate_stdout_limit'
    print(raw)
def write_new(path, value):
    raw=(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    if path.exists():
        assert path.read_bytes()==raw, 'immutable_control_receipt_conflict'
    else:
        with path.open('xb') as out:
            os.chmod(path, 0o600); out.write(raw); out.flush(); os.fsync(out.fileno())
@contextlib.contextmanager
def control_lock():
    with (C/'ASTRA_CONTROL_PRIVATE.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
def worker_active(directory, filename):
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args=path.read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            continue
        if any(x.endswith(('/'+filename).encode()) for x in args):
            if any(args[i]==b'--directory' and args[i+1]==str(directory).encode() for i in range(len(args)-1)):
                return True
    return False
def ledger(directory, required=False):
    path=directory/'ADMISSION_PRIVATE.sqlite3'
    if not path.exists():
        assert not required, 'admission_ledger_missing'
        return {'physical_attempts':0, 'logical_calls':0, 'reserved_nano':0, 'attempt_states':{},
                'input_tokens':0, 'output_tokens':0, 'admission_hold':False}
    db=sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        count, logical, nano=db.execute('select count(*),count(distinct context),coalesce(sum(dollars_nano),0) from attempts').fetchone()
        states=dict(db.execute('select state,count(*) from attempts group by state'))
        details=[json.loads(row[0]) for row in db.execute('select detail from attempts')]
    finally:
        db.close()
    safe_states={state:states[state] for state in KNOWN_STATES if state in states}
    other=sum(value for state,value in states.items() if state not in KNOWN_STATES)
    if other: safe_states['other']=other
    return {'physical_attempts':count, 'logical_calls':logical, 'reserved_nano':nano,
        'attempt_states':safe_states, 'admission_hold':bool(HOLD_STATES & set(states)),
        'input_tokens':sum((x.get('usage') or {}).get('prompt_tokens',0) for x in details),
        'output_tokens':sum((x.get('usage') or {}).get('completion_tokens',0) for x in details)}
def check_astra_cap(value):
    for key, cap in (('physical_attempts',6), ('logical_calls',6), ('reserved_nano',8_000_000_000)):
        assert type(value[key]) is int and 0 <= value[key] <= cap, 'astra_admission_cap_breach'
def run_private(command, name):
    path=S/(name+'_'+str(time.time_ns())+'_EXECUTION_PRIVATE.json')
    try:
        cp=subprocess.run(command, capture_output=True, text=True, timeout=240)
    except Exception as exc:
        write_new(path, {'error_type':type(exc).__name__, 'details':str(exc)})
        raise AssertionError(name+'_failed_private_details_retained') from None
    write_new(path, {'returncode':cp.returncode, 'stdout':cp.stdout, 'stderr':cp.stderr})
    assert cp.returncode==0, name+'_failed_private_details_retained'
def context():
    # Every artifact is verified in place. No runtime installation or refreeze.
    for name, digest in EXPECTED_FILES.items():
        assert sha(C/name)==digest, 'frozen_runtime_or_protocol_changed'
    sys.path.insert(0,str(P)); sys.path.insert(0,str(V))
    import cloud_score_adapter as adapter
    import stage5_common as common
    policy=common.MODELS['Astra']
    assert policy['physical']==6 and policy['logical']==6 and policy['cap_nano']==8_000_000_000
    assert common.NEW_CAP_NANO==50_000_000_000 and sum(x['cap_nano'] for x in common.MODELS.values())==50_000_000_000
    freeze=read(C/'EXECUTION_FREEZE_PUBLIC.json')
    assert freeze['frame_count']==135 and freeze['new_cap_usd']==50 and freeze['model_calls']==0
    assert sha(L/'INPUT_PINS_PUBLIC.json')==freeze['runtime_input_pin_sha256']
    original=read(L/'INPUT_PINS_PUBLIC.json')
    assert all(sha(V/name)==digest for name,digest in original['code_sha256'].items())
    frame, frame_freeze=adapter.load_frame(C/'FRAME_PRIVATE.jsonl',C/'FRAME_FREEZE_PUBLIC.json')
    assert len(frame)==135 and frame_freeze['frame_sha256']==freeze['frame_freeze']['frame_sha256']
    roster=common.roster_sha256(frame)
    prior_total=0
    for directory, leg, cap in ((L,'Luna',2_000_000_000),(K,'Kimi',40_000_000_000)):
        final=read(directory/(leg.upper()+'_FINAL_PUBLIC.json'))
        assert final['leg']==leg and final['runtime_version']==common.VERSION
        assert final['terminal_no_active_requests'] is True and final['outputs_accounted']==135
        assert final['roster_sha256']==roster and final['output_roster_sha256']==roster
        assert type(final['reserved_nano']) is int and 0<=final['reserved_nano']<=cap
        assert sha(directory/'OUTPUTS_PRIVATE.jsonl')==final['output_sha256']
        assert sha(directory/'EXCLUSIONS_EXPORT_PRIVATE.json')==final['exclusions_sha256']
        snapshot=ledger(directory, required=True)
        assert not snapshot['admission_hold'], 'predecessor_admission_hold'
        for name in ('physical_attempts','logical_calls','reserved_nano'):
            assert snapshot[name]==final[name], 'predecessor_final_ledger_mismatch'
        prior_total+=final['reserved_nano']
    assert not worker_active(K,'stage5_kimi_worker.py'), 'Kimi_worker_still_active'
    assert not worker_active(L,'stage5_cloud_worker.py'), 'Luna_worker_still_active'
    assert prior_total+8_000_000_000 <= 50_000_000_000, 'all_legs_reservation_cap'
    public=read(S/'SCORING_PUBLIC.json'); count=public['astra_source_only_requests']
    assert type(count) is int and 1<=count<=6, 'astra_requires_one_to_six_scored_source_requests'
    assert public['status']=='frozen_primary_scored_astra_prepared_not_called'
    assert public['primary_gate_unchanged'] is True and public['primary_reference_overwritten'] is False
    assert public['production_admission'] is False and public['model_calls_by_adapter']==0
    assert public['scores_sha256']==sha(S/'SCORES_PRIVATE.json') and public['frame_sha256']==frame_freeze['frame_sha256']
    scores=read(S/'SCORES_PRIVATE.json'); protocol=read(P/'CONFIRMATION_PROTOCOL.json')
    assert scores['protocol_version']==public['protocol_version']==protocol['version']
    assert scores['accounting']['frame_cases']==135
    assert scores['freeze_binding']['frame_sha256']==frame_freeze['frame_sha256']
    assert scores['freeze_binding']['protocol_bundle_sha256']==frame_freeze['protocol_bundle_sha256']
    queue=scores['bounded_astra_diagnostic_queue']
    assert queue==read(S/'ASTRA_SELECTION_PRIVATE.json') and 1<=len(queue)<=6
    assert queue==sorted(queue,key=lambda row:(row['rank_sha256'],row['record_id']))
    assert all(row['rank_sha256']==adapter.scorer.digest_json([scores['protocol_version'],*adapter.identity(row)]) for row in queue)
    selected={adapter.identity(row) for row in queue}
    assert len(selected)==len(queue) and selected<={adapter.identity(row) for row in frame}
    original_meta=adapter.read_metadata(K/'INPUTS_PRIVATE.jsonl')
    assert set(original_meta)=={adapter.identity(row) for row in frame}
    exclusions=adapter.exclusions_union([L/'EXCLUSIONS_EXPORT_PRIVATE.json',K/'EXCLUSIONS_EXPORT_PRIVATE.json'])
    allowed={key for key in selected if not adapter.excluded(key,(original_meta[key],),exclusions)}
    requests_meta=adapter.read_metadata(S/'ASTRA_INPUTS_PRIVATE.jsonl')
    assert set(requests_meta)==allowed and len(allowed)==count, 'scored_source_selection_changed'
    # Decode only eligible source bodies, after exclusion metadata has been checked.
    sources=adapter.read_selected(K/'INPUTS_PRIVATE.jsonl',allowed)
    requests=adapter.read_selected(S/'ASTRA_INPUTS_PRIVATE.jsonl',allowed)
    for key in allowed:
        source=sources[key]
        expected={'case':source['case'],'row':{name:source['row'][name] for name in (*adapter.IDENTITY,'full_document')},
                  'protected':False,'fresh_never_exposed':True,'partition':'confirmation'}
        assert requests[key]==expected, 'astra_input_not_exact_source_only_packet'
        assert hashlib.sha256(expected['row']['full_document'].encode()).hexdigest()==key[1]
    assert read(S/'JOIN_PUBLIC.json')['cases_sha256']==sha(S/'JOINED_CASES_PRIVATE.jsonl')
    names=('FRAME_PRIVATE.jsonl','FRAME_FREEZE_PUBLIC.json','EXECUTION_FREEZE_PUBLIC.json',
        'luna/LUNA_FINAL_PUBLIC.json','luna/EXCLUSIONS_EXPORT_PRIVATE.json',
        'kimi_direct_v4/KIMI_FINAL_PUBLIC.json','kimi_direct_v4/INPUTS_PRIVATE.jsonl',
        'kimi_direct_v4/SCHEMA.json','kimi_direct_v4/INSTRUCTIONS.md','kimi_direct_v4/EXCLUSIONS_EXPORT_PRIVATE.json',
        'scoring_v1/SCORING_PUBLIC.json','scoring_v1/SCORES_PRIVATE.json','scoring_v1/ASTRA_SELECTION_PRIVATE.json',
        'scoring_v1/ASTRA_INPUTS_PRIVATE.jsonl','scoring_v1/JOIN_PUBLIC.json','scoring_v1/JOINED_CASES_PRIVATE.jsonl')
    binding={name:sha(C/name) for name in names}
    return count, binding, common, [x['id'] for x in protocol['measures']]
def prepared(count,binding,common):
    assert read(BINDING)==binding, 'astra_predecessor_or_primary_binding_changed'
    receipt=read(PREPARE)
    assert receipt['binding_sha256']==sha(BINDING) and receipt['selected']==count
    items,pins=common.load_inputs(A,'Astra')
    assert len(items)==count and len(read(A/'FRAME_ROSTER_PRIVATE.json'))==135
    assert not any(common.blocked(item) for item in items), 'unexpected_source_subset_block'
    assert read(A/'PREFLIGHT_PUBLIC.json')['policy']==common.MODELS['Astra']
    assert sha(A/'INPUT_PINS_PUBLIC.json')==receipt['input_pins_sha256']
    assert sha(A/'KIMI_FINAL_PUBLIC.json')==sha(K/'KIMI_FINAL_PUBLIC.json')
    assert sha(A/'PREDECESSOR_EXCLUSIONS_PRIVATE.json')==sha(K/'EXCLUSIONS_EXPORT_PRIVATE.json')
    expected=[common.parse_json(x) for x in (S/'ASTRA_INPUTS_PRIVATE.jsonl').read_bytes().splitlines() if x.strip()]
    assert items==expected, 'prepared_source_subset_changed'
    return receipt,items,pins
def no_prior_launch():
    assert not LAUNCH.exists() and not INTENT.exists(), 'prior_astra_launch_no_resubmission'
    assert not (A/'ADMISSION_PRIVATE.sqlite3').exists(), 'prior_astra_admission_no_resubmission'
    assert not (A/'ASTRA_FINAL_PUBLIC.json').exists() and not (A/'OUTPUTS_PRIVATE.jsonl').exists()
    assert not (A/'WORKER_PRIVATE.log').exists() and not (A/'WORKER.lock').exists(), 'prior_astra_worker_trace'
    assert not any((A/'results').glob('*')), 'prior_astra_result_no_resubmission'
    assert not worker_active(A,'stage5_cloud_worker.py'), 'Astra_worker_active'
def terminal(count, common, items, pins):
    assert not worker_active(A,'stage5_cloud_worker.py'), 'Astra_worker_still_active'
    snapshot=ledger(A,required=True); check_astra_cap(snapshot)
    final=read(A/'ASTRA_FINAL_PUBLIC.json'); check_astra_cap(final)
    assert final['leg']=='Astra' and final['runtime_version']==common.VERSION
    assert final['terminal_no_active_requests'] is True and not snapshot['admission_hold']
    assert final['outputs_accounted']==count and final['selected']==count
    assert type(final['field_validation_complete']) is int and 0<=final['field_validation_complete']<=count
    assert final['roster_sha256']==pins['roster_sha256']
    assert final['input_pins_sha256']==sha(A/'INPUT_PINS_PUBLIC.json')
    assert final['output_roster_sha256']==common.roster_sha256(items)
    assert final['output_sha256']==sha(A/'OUTPUTS_PRIVATE.jsonl')
    assert final['exclusions_sha256']==sha(A/'EXCLUSIONS_EXPORT_PRIVATE.json')
    for key in ('physical_attempts','logical_calls','reserved_nano'):
        assert final[key]==snapshot[key], 'astra_final_ledger_mismatch'
    return final,snapshot
'''

PREPARE_ACTION = r'''
with control_lock():
    count,binding,common,measure_ids=context(); no_prior_launch()
    if PREPARE.exists():
        receipt,items,pins=prepared(count,binding,common)
    else:
        repo=C/'repo'; fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py'
        ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
        command=[sys.executable,'-B',str(V/'stage5_prepare.py'),'--leg','Astra','--directory',str(A),
            '--inputs',str(S/'ASTRA_INPUTS_PRIVATE.jsonl'),'--roster',str(C/'FRAME_PRIVATE.jsonl'),
            '--schema',str(K/'SCHEMA.json'),'--instructions',str(K/'INSTRUCTIONS.md'),
            '--exclusions',str(K/'EXCLUSIONS_EXPORT_PRIVATE.json'),'--field-validator',str(fv),
            '--frozen-validator',str(ov),'--predecessor-receipt',str(K/'KIMI_FINAL_PUBLIC.json'),
            '--predecessor-exclusions',str(K/'EXCLUSIONS_EXPORT_PRIVATE.json')]
        run_private(command,'ASTRA_PREPARE')
        write_new(BINDING,binding)
        receipt={'status':'bounded_Astra_source_only_prepared_not_launched','selected':count,'shared_roster_count':135,
            'binding_sha256':sha(BINDING),'input_pins_sha256':sha(A/'INPUT_PINS_PUBLIC.json'),
            'physical_request_cap':6,'Astra_cap_usd':8,'all_legs_cap_usd':50,'new_model_calls':0,
            'primary_reference_overwritten':False,'production_admission':False}
        write_new(PREPARE,receipt); prepared(count,binding,common)
    emit(receipt)
'''

LAUNCH_ACTION = r'''
with control_lock():
    count,binding,common,measure_ids=context(); prepared(count,binding,common); no_prior_launch()
    repo=C/'repo'; fv=repo/'linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py'
    ov=repo/'linkup/formal800_20261012/code/validate_reviews.py'
    # Persist before Popen: a lost response or interrupted launch cannot resubmit.
    write_new(INTENT,{'status':'launch_intent_no_automatic_retry','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'prepare_sha256':sha(PREPARE),'binding_sha256':sha(BINDING)})
    command=[sys.executable,'-B',str(V/'stage5_cloud_worker.py'),'--leg','Astra','--directory',str(A),
        '--field-validator',str(fv),'--frozen-validator',str(ov),'--workflow-directory',str(R/'code'),
        '--max-wall-seconds','14400']
    try:
        with (A/'WORKER_PRIVATE.log').open('xb') as log:
            worker=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    except Exception as exc:
        write_new(C/'ASTRA_LAUNCH_FAILURE_PRIVATE.json',{'error_type':type(exc).__name__,'details':str(exc)})
        raise AssertionError('astra_launch_failed_intent_retained_no_automatic_retry') from None
    receipt={'status':'bounded_Astra_diagnostic_launched_not_completion','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'pid':worker.pid,'selected':count,'shared_roster_count':135,'max_wall_seconds':14400,
        'physical_request_cap':6,'Astra_cap_usd':8,'all_legs_cap_usd':50,'identity_type':'existing_VM_managed_identity',
        'primary_reference_overwritten':False,'production_admission':False}
    write_new(LAUNCH,receipt); emit(receipt)
'''

STATUS_ACTION = r'''
count,binding,common,measure_ids=context()
receipt,items,pins=prepared(count,binding,common)
snapshot=ledger(A); check_astra_cap(snapshot)
active=worker_active(A,'stage5_cloud_worker.py')
result={'status':'bounded_Astra_diagnostic_snapshot','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'launched':LAUNCH.exists(),'launch_intent_exists':INTENT.exists(),'process_active':active,'selected':count,
    'shared_roster_count':135,'terminal_no_active_requests':False,'final_exists':(A/'ASTRA_FINAL_PUBLIC.json').exists(),
    'physical_request_cap':6,'Astra_cap_usd':8,'all_legs_cap_usd':50,
    'private_log_exists':(A/'WORKER_PRIVATE.log').exists(),'primary_reference_overwritten':False,'production_admission':False,
    **snapshot}
if result['final_exists'] and not active:
    final=read(A/'ASTRA_FINAL_PUBLIC.json')
    if final.get('terminal_no_active_requests') is True:
        final,snapshot=terminal(count,common,items,pins)
        result.update(terminal_no_active_requests=True,outputs_accounted=final['outputs_accounted'],
            field_validation_complete=final['field_validation_complete'],output_sha256=final['output_sha256'])
    else: result['status']='bounded_Astra_diagnostic_stopped_hold_no_retry'
emit(result)
'''

DIAGNOSE_ACTION = r'''
with control_lock():
    count,binding,common,measure_ids=context(); receipt,items,pins=prepared(count,binding,common)
    final,snapshot=terminal(count,common,items,pins)
    path=S/'ASTRA_DIAGNOSTIC_PUBLIC.json'
    if not path.exists():
        command=[sys.executable,'-B',str(P/'astra_diagnostic_compare.py'),
            '--frame',str(C/'FRAME_PRIVATE.jsonl'),'--frame-freeze',str(C/'FRAME_FREEZE_PUBLIC.json'),
            '--scores',str(S/'SCORES_PRIVATE.json'),'--joined-cases',str(S/'JOINED_CASES_PRIVATE.jsonl'),
            '--join-receipt',str(S/'JOIN_PUBLIC.json'),'--astra-inputs',str(S/'ASTRA_INPUTS_PRIVATE.jsonl'),
            '--astra-outputs',str(A/'OUTPUTS_PRIVATE.jsonl'),'--astra-final',str(A/'ASTRA_FINAL_PUBLIC.json'),
            '--exclusions',str(L/'EXCLUSIONS_EXPORT_PRIVATE.json'),str(K/'EXCLUSIONS_EXPORT_PRIVATE.json'),str(A/'EXCLUSIONS_EXPORT_PRIVATE.json'),
            '--repo',str(C/'repo'),'--output',str(path)]
        run_private(command,'ASTRA_DIAGNOSE')
    assert all(sha(C/name)==digest for name,digest in binding.items()), 'primary_artifact_changed_by_diagnostics'
    public=validate_diagnostic(parse_diagnostic(path.read_bytes()),measure_ids)
    assert public['original_primary_scores_sha256']==sha(S/'SCORES_PRIVATE.json')
    assert public['astra_outputs_sha256']==final['output_sha256'] and public['source_only_requests']==count
    assert public['physical_attempts']==final['physical_attempts'] and public['reserved_usd']==final['reserved_nano']/1e9
    import urllib.error
    sys.path.insert(0,str(R/'code')); from workflow import call
    raw=path.read_bytes(); assert len(raw)<=1_000_000
    url='https://stlinkup70d455c0261104.blob.core.windows.net/astra-handoff/'+BLOB_KEY
    try:
        with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
            assert response.read(1_000_001)==raw, 'diagnostic_blob_conflict'
    except urllib.error.HTTPError as exc:
        if exc.code!=404: raise
        with call(url,'https://storage.azure.com/',method='PUT',body=raw,
                  headers={'x-ms-version':'2023-11-03','x-ms-blob-type':'BlockBlob','If-None-Match':'*'}) as response:
            assert response.status==201
    with call(url,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
        assert response.read(1_000_001)==raw, 'diagnostic_blob_verification_failed'
    transport={'status':'bounded_Astra_diagnostic_summary_verified','bytes':len(raw),'sha256':sha(path),'blob_key':BLOB_KEY,
        'source_only_requests':count,'physical_attempts':final['physical_attempts'],'reserved_usd':final['reserved_nano']/1e9,
        'original_primary_scores_sha256':sha(S/'SCORES_PRIVATE.json'),'new_model_calls_by_diagnostic_tool':0,
        'reference_overwritten':False,'primary_gates_recomputed':False,'production_admission':False}
    write_new(TRANSPORT,transport); emit(transport)
'''


def _source(base, action):
    pins = {name: hashlib.sha256((D / name).read_bytes()).hexdigest() for name in PINNED_FILES}
    source = (base + '\nimport time\nEXPECTED_FILES=' + repr(pins) + '\nBLOB_KEY=' + repr(BLOB_KEY)
              + '\n' + PUBLIC_VALIDATION + COMMON + action)
    compile(source, '<stage5-astra-control>', 'exec')
    return source


def _remote(control, base, action, name, filename):
    result = control.vm(_source(base, action), 'stage5_' + name + '_' + str(time.time_ns()))
    encoded = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False)
    assert len(encoded.encode()) < 4096, 'aggregate_stdout_limit'
    control.save(D / 'control' / filename, result)
    print(encoded)
    return result


def prepare(control, base):
    return _remote(control, base, PREPARE_ACTION, 'prepare_astra', 'ASTRA_PREPARE_PUBLIC.json')


def launch(control, base):
    return _remote(control, base, LAUNCH_ACTION, 'launch_astra', 'ASTRA_LAUNCH_PUBLIC.json')


def status(control, base):
    return _remote(control, base, STATUS_ACTION, 'status_astra', 'ASTRA_STATUS_' + str(time.time_ns()) + '_PUBLIC.json')


def diagnose(control, base):
    return _remote(control, base, DIAGNOSE_ACTION, 'diagnose_astra', 'ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json')


def download(control, base):
    import os
    import sys
    transport = json.loads((D / 'control/ASTRA_DIAGNOSTIC_TRANSPORT_PUBLIC.json').read_text())
    assert transport['status'] == 'bounded_Astra_diagnostic_summary_verified'
    assert transport['blob_key'] == BLOB_KEY and 0 < transport['bytes'] <= 1_000_000
    sys.path.insert(0, str(D.parent / 'continuation_dispatch_20261117'))
    import storage_transport as storage
    with storage.call(storage.HOST + '/' + storage.CONTAINER + '/' + BLOB_KEY, storage.storage_token()) as response:
        raw = response.read(1_000_001)
    assert len(raw) == transport['bytes'] and hashlib.sha256(raw).hexdigest() == transport['sha256']
    protocol = json.loads((D / 'protocol/CONFIRMATION_PROTOCOL.json').read_text())
    public = validate_diagnostic(parse_diagnostic(raw), [x['id'] for x in protocol['measures']])
    assert public['original_primary_scores_sha256'] == transport['original_primary_scores_sha256']
    for key in ('source_only_requests', 'physical_attempts', 'reserved_usd'):
        assert public[key] == transport[key]
    path = D / 'ASTRA_DIAGNOSTIC_PUBLIC.json'
    if path.exists():
        assert path.read_bytes() == raw, 'local_diagnostic_conflict'
    else:
        with path.open('xb') as out:
            os.chmod(path, 0o600); out.write(raw); out.flush(); os.fsync(out.fileno())
    result = {'status':'bounded_Astra_diagnostic_download_verified', 'source_only_requests':public['source_only_requests'],
        'physical_attempts':public['physical_attempts'], 'reserved_usd':public['reserved_usd'],
        'reference_overwritten':False, 'primary_gates_recomputed':False, 'production_admission':False}
    print(json.dumps(result, sort_keys=True))
    return result


def dispatch(action, control, base):
    return {'prepare_astra':prepare, 'launch_astra':launch, 'status_astra':status,
            'diagnose_astra':diagnose, 'download_astra':download}[action](control, base)
