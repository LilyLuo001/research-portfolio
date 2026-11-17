"""Start one bounded existing-value projection, without timers or model calls."""
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
    lock=(out/'LAUNCH.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    receipt=out/'LAUNCH_PUBLIC.json'
    assert not receipt.exists(), 'existing_launch_preserved_do_not_duplicate'
    assert not (out/'LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite').exists(), 'existing_output_preserved'
    assert not (out/'FAILURE_PUBLIC.json').exists(), 'inspect_existing_failure_before_launch'
    pins=json.loads((out/'RUN_PINS_PUBLIC.json').read_text())
    for name,digest in pins['code_and_contract'].items():
        assert Path(name).name==name
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert (out/'RECONCILED_STATE_V3_PRIVATE.sqlite').exists()
    active=[]
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args=path.read_bytes().split(b'\0')
            if any(Path(x.decode(errors='replace')).name=='cloud_materialize.py' for x in args if x):
                active.append(int(path.parent.name))
        except (OSError, ValueError):
            pass
    assert not active, 'existing_materialization_process_preserved'
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    with (out/'MATERIALIZE_STDOUT_PRIVATE.log').open('xb') as log:
        worker=subprocess.Popen([sys.executable,'-u',str(out/'cloud_materialize.py')],cwd=out,
             stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
             start_new_session=True,env=env)
    data={'status':'bounded_reuse_worker_launched_not_yet_complete',
          'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':worker.pid,
          'worker_relative_to_migration':'reuse_execution_20261117/run001/cloud_materialize.py',
          'code_and_contract_sha256':pins['code_and_contract'],
          'max_wall_seconds':10800,'max_output_bytes':16*1024**3,
          'new_model_calls':0,'new_production_accepted':0,'timers_created_or_resumed':False,
          'new_resources_created':False,'source_database_read_only':True}
    receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(data))


if __name__=='__main__':
    main()
