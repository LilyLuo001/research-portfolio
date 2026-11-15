"""Serialized, compressed Azure control plane. Never prints private ARM responses."""
import base64,fcntl,hashlib,json,os,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).parent
REVIEW=HERE.parent
W=Path.home()/'.local/share/opencode/private/linkup-qualification350-20261116'
HELPER=Path.home()/'Documents/LinkUp_Research_20260924/reproducibility_git/linkup/azure_resume_20261110/arm_vm_exec.py'
LOCK=Path.home()/'.local/share/opencode/private/linkup-kimi-bulk1309-20261115/VM_CONTROL.lock'
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    with t.open('w') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def vm(source,tag):
    os.umask(0o077)
    p=W/'controls'/f'{tag}.py';p.parent.mkdir(exist_ok=True)
    wrapper="import base64,zlib\nexec(compile(zlib.decompress(base64.b64decode("+repr(base64.b64encode(zlib.compress(source.encode(),9)).decode())+")), '<bounded-cloud-control>', 'exec'))\n"
    assert len(base64.b64encode(wrapper.encode()))+512<120000,'control_requires_split_no_execution'
    if p.exists():assert p.read_text()==wrapper,'control_name_collision'
    else:p.write_text(wrapper)
    with LOCK.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        cp=subprocess.run([sys.executable,str(HELPER),str(p)],capture_output=True,text=True,timeout=1320)
    # This copy is private; signed ARM polling URLs must never enter reports.
    save(p.with_suffix('.response_PRIVATE.json'),{'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
    if cp.returncode:raise RuntimeError('ARM_control_failed_private_receipt_retained')
    records=[json.loads(l) for l in cp.stdout.splitlines() if l.startswith('{')]
    result=next(x for x in records if 'value' in x)
    msg=next(x['message'] for x in result['value'] if '[stdout]' in x.get('message',''))
    body=msg.split('[stdout]\n',1)[1].split('\n[stderr]',1)[0].strip()
    try:return json.loads(body)
    except Exception:raise RuntimeError('cloud_script_no_valid_JSON_success_receipt') from None

