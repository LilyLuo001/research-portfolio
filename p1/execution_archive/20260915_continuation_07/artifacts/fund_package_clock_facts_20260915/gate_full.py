#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
ap=argparse.ArgumentParser()
for x in ['manifest','pilot_receipt','code','facts','mapping','pairs','outdir']:ap.add_argument('--'+x,required=True)
a=ap.parse_args();m=json.load(open(a.manifest));p=json.load(open(a.pilot_receipt))
assert m['contract_sha256']=='00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f'
for k,path in [('code',a.code),('facts',a.facts),('mapping',a.mapping)]:assert sha(path)==m['sha256'][k]
assert p['mode']=='pilot' and p['status']=='PROTECTED_MEMBERSHIP_SIDECAR_COMPLETE' and all(p['invariants'].values())
assert p['code_sha256']==m['sha256']['code'] and p['contract_sha256']==m['contract_sha256']
assert p['counts']['candidate_denominator']==20 and p['counts']['exact_series_membership_rows']>=20
assert m['sha256']['facts'] in p['input_sha256'].values()
assert m['sha256']['mapping'] in p['input_sha256'].values()
# Only now open/hash the full protected input.
assert sha(a.pairs)==m['sha256']['full_pairs']
token=Path(a.outdir).parent/'FULL_GATE_TOKEN.json'; token.write_text(json.dumps({'status':'FULL_GATE_AUTHORIZED','contract_sha256':m['contract_sha256'],'sha256':{k:m['sha256'][k] for k in ['code','facts','mapping','full_pairs']},'manifest_sha256':sha(a.manifest),'pilot_receipt_sha256':sha(a.pilot_receipt)},indent=2)+'\n')
subprocess.run([sys.executable,a.code,'--pairs',a.pairs,'--mapping',a.mapping,'--facts',a.facts,'--outdir',a.outdir,'--mode','full','--gate-token',str(token)],check=True)
print('FULL_GATE_PASS')
