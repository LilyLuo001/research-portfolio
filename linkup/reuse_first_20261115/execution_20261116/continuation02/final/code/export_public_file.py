"""Bounded, SHA-verified public report transport; no raw research data or credentials."""
import base64,hashlib,json,math,sys,zlib
from control import HERE,vm,save
ALLOWED={'QUALIFICATION_COMPARISON_PUBLIC.json','QUALIFICATION_DECISION_PUBLIC.json','INDEPENDENT_AUDIT_PUBLIC.json','ASTRA_AUDIT_SELECTION_PUBLIC.json'}
def export(name):
 assert name in ALLOWED
 root="from pathlib import Path\nimport base64,hashlib,json,zlib\np=Path.home()/'migration/execution_20261116/run001/continuation02'/"+repr(name)+"\nb=p.read_bytes();s=base64.b64encode(zlib.compress(b,9)).decode()\n"
 tag='public_'+name.lower().replace('.json','')
 meta=vm(root+"print(json.dumps({'length':len(s),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}))",tag+'_meta')
 parts=[]
 for i in range(math.ceil(meta['length']/2800)):
  r=vm(root+f"assert hashlib.sha256(b).hexdigest()=={meta['sha256']!r}\nprint(json.dumps({{'chunk':s[{i*2800}:{(i+1)*2800}]}}))",tag+'_'+str(i));parts.append(r['chunk'])
 b=zlib.decompress(base64.b64decode(''.join(parts)));assert len(b)==meta['bytes'] and hashlib.sha256(b).hexdigest()==meta['sha256'];x=json.loads(b);(HERE/name).write_bytes(b);return x
if __name__=='__main__':
 for name in sys.argv[1:]:
  x=export(name);print(json.dumps({'file':name,'verified':True,'bytes':(HERE/name).stat().st_size}),flush=True)
