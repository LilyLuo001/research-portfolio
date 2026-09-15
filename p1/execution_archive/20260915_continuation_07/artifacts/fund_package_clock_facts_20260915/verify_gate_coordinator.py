"""Small negative tests: no protected source data is needed or read."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path

base=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args): return subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True)
fixture=run([base/'test_facts.py']); assert fixture.returncode==0,fixture.stderr
with tempfile.TemporaryDirectory(prefix='p1-gate-negative-') as temp:
    t=Path(temp); missing=t/'MUST_NOT_READ.csv'
    bare=run([base/'build_protected_membership_sidecar.py','--mode','full','--pairs',missing,'--facts',missing,'--mapping',missing,'--outdir',t/'bare'])
    assert bare.returncode and 'full mode requires gate token' in bare.stderr
    facts=t/'facts'; mapping=t/'mapping'
    facts.write_text('synthetic facts'); mapping.write_text('synthetic mapping')
    contract='00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f'
    code=base/'build_protected_membership_sidecar.py'
    manifest={'contract_sha256':contract,'sha256':{'code':sha(code),'facts':sha(facts),'mapping':sha(mapping),'full_pairs':'not-read'}}
    pilot={'mode':'pilot','status':'PROTECTED_MEMBERSHIP_SIDECAR_COMPLETE','invariants':{'fixture':True},'code_sha256':sha(code),'contract_sha256':contract,'counts':{'candidate_denominator':20,'exact_series_membership_rows':20},'input_sha256':{'facts':'STALE','mapping':sha(mapping)}}
    mf=t/'manifest.json'; pr=t/'pilot.json'
    mf.write_text(json.dumps(manifest)); pr.write_text(json.dumps(pilot))
    stale=run([base/'gate_full.py','--manifest',mf,'--pilot_receipt',pr,'--code',code,'--facts',facts,'--mapping',mapping,'--pairs',missing,'--outdir',t/'full'])
    assert stale.returncode and 'AssertionError' in stale.stderr and 'FileNotFoundError' not in stale.stderr
receipt={'status':'PASS','fixture_script_pass':True,'direct_full_without_gate_rejected_before_data_read':True,'stale_pilot_facts_rejected_before_full_input_read':True,'protected_data_read':False,'verification_role':'COORDINATOR_NOT_SEPARATE_REFEREE','code_sha256':{p.name:sha(p) for p in [base/'build_protected_membership_sidecar.py',base/'gate_full.py',base/'test_facts.py',Path(__file__)]}}
(base/'COORDINATOR_GATE_CHECK.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
