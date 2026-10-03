#!/usr/bin/env python3
"""Bind the P4 review frame to completed narrow and global uniqueness receipts."""
import argparse,hashlib,json,os
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--narrow-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-canonical-rows',type=int,required=True);p.add_argument('--verified-usable-rows',type=int,required=True);a=p.parse_args()
 audit=json.loads(a.audit.read_text());narrow=json.loads(a.narrow_receipt.read_text())
 if audit.get('status')!='complete' or audit.get('rows')!=a.expected_canonical_rows:raise RuntimeError('global JOB_HASH audit incomplete or wrong population')
 if narrow.get('status')!='complete' or narrow.get('shards')!=2464:raise RuntimeError('narrow receipt incomplete')
 if audit.get('duplicate_job_hashes')!=0 or audit.get('duplicate_occurrences')!=0:raise RuntimeError('nonzero duplicates require an independently verified usable anti-join row count')
 value={'key_namespace':'linkup_job_source_record_tuple_json_v1','stable_key_type':'string','verified_unique_private_keys':True,'verified_full_frame_rows':a.verified_usable_rows,'source_provenance':'full 2464-shard semantic narrow, usable=true, after completed global JOB_HASH audit','source_receipts':['narrow:'+sha(a.narrow_receipt),'global_job_hash_audit:'+sha(a.audit)],'global_audit_counts':{k:audit[k] for k in ('rows','distinct_job_hashes','duplicate_job_hashes','duplicate_occurrences')}}
 a.output.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(a.output)+'.tmp');tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');os.chmod(tmp,0o600);os.replace(tmp,a.output)
 print(json.dumps({'status':'complete','verified_full_frame_rows':a.verified_usable_rows,'audit_sha256':sha(a.audit)}))
if __name__=='__main__':main()
