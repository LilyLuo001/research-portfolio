#!/bin/bash -l
#$ -cwd
#$ -j y
#$ -P econdept
#$ -q econ
#$ -pe omp 1
#$ -l h_rt=00:10:00
#$ -l mem_per_core=2G
#$ -l no_gpu=TRUE
#$ -N lk_ksip
set -euo pipefail
umask 077
CREDS=/projectnb/econdept/qluo/.linkup_transfer_credentials_20261010
START=$(date +%s%N)
BYTES=$(ssh -4 -i "$CREDS/source_ks_id" -p 65023 -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$CREDS/known_hosts" -o IdentitiesOnly=yes -o HostKeyAlias="[cancon.hpccube.com]:65023" -o ConnectTimeout=15 -o ServerAliveInterval=20 -o ServerAliveCountMax=2 lilysharp@223.113.240.51 'head -c 16777216 -- /public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions/job-descriptions_0_0_20.snappy.parquet' | wc -c)
END=$(date +%s%N)
python3 - "$BYTES" "$START" "$END" <<'PY'
import json,sys,time,os
b=int(sys.argv[1]); elapsed=(int(sys.argv[3])-int(sys.argv[2]))/1e9
p='/projectnb/econdept/qluo/linkup_rulefirst_20261008/continuation_20261010/public/KS_ALT_IPV4_PROBE_PUBLIC.json';t=p+'.tmp'
open(t,'w').write(json.dumps({'status':'complete' if b==16777216 else 'fail','bytes':b,'elapsed_seconds':elapsed,'bytes_per_second':b/elapsed if elapsed else None,'address_family':'inet','endpoint_alias':'kunshan_alternate_ipv4_2','job_id':os.environ.get('JOB_ID'),'created_epoch':time.time()},indent=2,sort_keys=True)+'\n');os.replace(t,p)
PY
