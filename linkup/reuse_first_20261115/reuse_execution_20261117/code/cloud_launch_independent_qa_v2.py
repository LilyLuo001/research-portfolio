"""Launch a single bounded read-only QA worker; no timers or model calls."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    os.umask(0o077)
    out=Path.home()/'migration/reuse_execution_20261117/run001'
    lock=(out/'QA_V2_LAUNCH.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt=out/'INDEPENDENT_QA_V2_LAUNCH_PUBLIC.json'
    assert not receipt.exists(), 'previous_QA_launch_preserved'
    assert not (out/'MATERIALIZATION_INDEPENDENT_QA_V2_PUBLIC.json').exists(), 'previous_QA_result_preserved'
    assert not (out/'INDEPENDENT_QA_V2_PROGRESS_PUBLIC.json').exists(), 'inspect_prior_QA_checkpoint_before_resume'
    material=json.loads((out/'MATERIALIZATION_PUBLIC.json').read_text())
    assert material['status']=='first_reuse_materialization_complete'
    pins=json.loads((out/'INDEPENDENT_QA_V2_DEPLOYMENT_PUBLIC.json').read_text())
    for name,digest in pins['files_sha256'].items():
        assert Path(name).name==name
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    names={'cloud_materialize.py','cloud_verify_materialization.py','cloud_verify_materialization_v2.py'}
    active=[]
    for proc in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args=proc.read_bytes().split(b'\0')
            if any(Path(x.decode(errors='replace')).name in names for x in args if x):
                active.append(int(proc.parent.name))
        except (OSError,ValueError):
            pass
    assert not active, 'existing_worker_preserved_no_duplicate_QA'
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    with (out/'INDEPENDENT_QA_V2_STDOUT_PRIVATE.log').open('xb') as log:
        worker=subprocess.Popen([sys.executable,'-u',str(out/'cloud_verify_materialization_v2.py')],
            cwd=out,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
            start_new_session=True,env=env)
    result={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'independent_readonly_QA_launched_not_yet_passed','pid':worker.pid,
        'files_sha256':pins['files_sha256'],'source_output_sha256':material['destination_sha256'],
        'worker_wall_limit_seconds':1800,'sqlite_cache_MiB':256,
        'materialization_restarted':False,'timers_created_or_resumed':False,
        'new_model_calls':0,'new_production_accepted':0,'new_resources_created':False}
    with receipt.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
