import hashlib,json
from pathlib import Path
R=Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/w021_preannouncement_exposure_repair_20260915')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((R/'golden_pilot_v3/RECEIPT.json').read_text())
bt=json.loads((R/'golden_pilot_v3/FIELDWISE_BACKTRACE.json').read_text())
ib=json.loads((R/'golden_pilot_v3/INDEPENDENT_BACKTRACE.json').read_text())
assert p['status']=='PASS' and p['candidate_positions']>=20 and p['fixture_assertions']>=5 and p['code_sha256']==sha(R/'run_w021_repair_v3.py') and bt['status']=='PASS' and bt['positions']>=20 and ib['status']=='PASS' and ib['source_hashes']=={k:p['source_hashes'][k] for k in ['projection','stocknames','dseshares']}
t={'status':'FULL_GATE_AUTHORIZED','golden_receipt_sha256':sha(R/'golden_pilot_v3/RECEIPT.json'),'golden_backtrace_sha256':sha(R/'golden_pilot_v3/FIELDWISE_BACKTRACE.json'),'code_sha256':p['code_sha256'],'config_sha256':p['config_sha256'],'source_hashes':p['source_hashes'],'pilot_invariants':{'status':p['status'],'candidate_positions':p['candidate_positions'],'fixture_assertions':p['fixture_assertions'],'backtrace_positions':bt['positions']},'contract_sha256':'00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f','pilot_precedes_full':True}
(R/'FULL_GATE_TOKEN_V3.json').write_text(json.dumps(t,indent=2,sort_keys=True)+'\n');print(json.dumps(t))
