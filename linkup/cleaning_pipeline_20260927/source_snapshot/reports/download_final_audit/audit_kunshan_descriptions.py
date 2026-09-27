#!/usr/bin/env python3
import datetime as dt, hashlib, json, os, re
from collections import Counter, defaultdict
from pathlib import Path
import pyarrow.parquet as pq

DATA=Path('/public/home/lilysharp/dewey_downloads/data/linkup_job_descriptions')
META=Path('/public/home/lilysharp/dewey_downloads/metadata/linkup_job_descriptions')
ASSIGNED_FILE=Path('/public/home/lilysharp/linkup_analysis_v1/stage_b/metadata/description_files.txt')
OUT=Path('/public/home/lilysharp/linkup_analysis_v1/stage_b/metadata/kunshan_description_final_audit.json')
CANON=META/'dewey-audit-manifest.json'
HASHES=META/'migration_source_hashes.json'
RECEIPTS=META/'bounded_receipts'
PAT=re.compile(r'^job-descriptions_.+\.snappy\.parquet$')

def sha(b): return hashlib.sha256(b).hexdigest()
def atomic_json(path,obj):
 t=Path(str(path)+'.tmp'); t.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str)+'\n'); os.replace(t,path)

started=dt.datetime.now(dt.timezone.utc)
canonical_doc=json.loads(CANON.read_text()); canonical={x['file_name']:x for x in canonical_doc['files']}
assigned_paths=[Path(x) for x in ASSIGNED_FILE.read_text().splitlines() if x.strip()]
assigned=[p.name for p in assigned_paths]
actual_files=sorted(p for p in DATA.iterdir() if p.is_file())
actual_formal={p.name:p for p in actual_files if PAT.match(p.name)}
remnants=[{'name':p.name,'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in actual_files if not PAT.match(p.name)]
pre={n:(p.stat().st_size,p.stat().st_mtime_ns) for n,p in actual_formal.items()}
missing=sorted(set(assigned)-set(actual_formal)); extra=sorted(set(actual_formal)-set(assigned))
unknown_assigned=sorted(set(assigned)-set(canonical))
size_mismatch=[]; zero=[]; tiny=[]; footer_errors=[]; schemas=defaultdict(list); rows=0; row_groups=0
canonical_min=min(x['file_size_bytes'] for x in canonical.values())
for n in sorted(set(assigned)&set(actual_formal)):
 p=actual_formal[n]; st=p.stat(); exp=canonical[n]['file_size_bytes']
 if st.st_size!=exp: size_mismatch.append({'file_name':n,'actual_bytes':st.st_size,'expected_bytes':exp})
 if st.st_size==0: zero.append(n)
 if st.st_size<1_000_000: tiny.append({'file_name':n,'bytes':st.st_size})
 try:
  pf=pq.ParquetFile(p); rows+=pf.metadata.num_rows; row_groups+=pf.metadata.num_row_groups
  sch=str(pf.schema_arrow); schemas[sha(sch.encode())].append(n)
 except Exception as e: footer_errors.append({'file_name':n,'error':repr(e)})
post={n:(p.stat().st_size,p.stat().st_mtime_ns) for n,p in actual_formal.items()}
changed=[{'file_name':n,'before':pre[n],'after':post.get(n)} for n in sorted(pre) if post.get(n)!=pre[n]]
# Existing full-content hashes: 1,348 migration hashes plus 10 strict validation receipts.
hash_doc=json.loads(HASHES.read_text()); hash_entries={x['file_name']:x for x in hash_doc['files']}
receipt_entries={}
receipt_errors=[]
for p in sorted(RECEIPTS.glob('*.json')):
 try:
  x=json.loads(p.read_text()); receipt_entries[x['file_name']]=x
 except Exception as e: receipt_errors.append({'file':p.name,'error':repr(e)})
sha_union=set(hash_entries)|set(receipt_entries)
sha_size_mismatch=[]
for n,x in {**hash_entries,**receipt_entries}.items():
 if n in canonical and x.get('file_size_bytes')!=canonical[n]['file_size_bytes']:
  sha_size_mismatch.append(n)
sha_invalid=sorted(n for n,x in {**hash_entries,**receipt_entries}.items() if not re.fullmatch(r'[0-9a-f]{64}',x.get('sha256','')))
receipt_footer_mismatch=[]
for n,x in receipt_entries.items():
 if n in actual_formal and 'rows' in x:
  try:
   rr=pq.ParquetFile(actual_formal[n]).metadata.num_rows
   if rr!=x['rows']: receipt_footer_mismatch.append({'file_name':n,'receipt_rows':x['rows'],'footer_rows':rr})
  except Exception: pass
assigned_bytes=sum(actual_formal[n].stat().st_size for n in set(assigned)&set(actual_formal))
expected_bytes=sum(canonical[n]['file_size_bytes'] for n in assigned if n in canonical)
result={
 'status':'PASS' if not any((missing,extra,unknown_assigned,size_mismatch,zero,tiny,footer_errors,changed,remnants,receipt_errors,sha_size_mismatch,sha_invalid,receipt_footer_mismatch)) and len(schemas)==1 and sha_union==set(assigned) else 'FAIL',
 'audit_started_utc':started.isoformat(),'audit_finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
 'read_only':True,'data_directory':str(DATA),
 'canonical':{'dataset_external_id':canonical_doc['describe']['dataset_external_id'],'dataset_version_timestamp':canonical_doc['describe']['dataset_version_timestamp'],
   'files':len(canonical),'bytes':sum(x['file_size_bytes'] for x in canonical.values()),'manifest_sha256':sha(CANON.read_bytes()),'minimum_expected_file_bytes':canonical_min},
 'assignment':{'source':str(ASSIGNED_FILE),'source_sha256':sha(ASSIGNED_FILE.read_bytes()),'entries':len(assigned),'distinct_names':len(set(assigned)),
   'expected_bytes':expected_bytes,'actual_bytes':assigned_bytes},
 'inventory':{'formal_parquet_files':len(actual_formal),'all_regular_files':len(actual_files),'missing_assigned':missing,'extra_formal':extra,
   'unknown_assigned':unknown_assigned,'part_or_temp_or_other_remnants':remnants,'zero_byte':zero,'tiny_under_1MB':tiny,
   'size_mismatches':size_mismatch,'files_changed_during_audit':changed},
 'parquet_footer':{'attempted':len(set(assigned)&set(actual_formal)),'readable':len(set(assigned)&set(actual_formal))-len(footer_errors),
   'errors':footer_errors,'total_rows':rows,'total_row_groups':row_groups,'schema_variant_count':len(schemas),
   'schema_variants':[{'schema_sha256':k,'file_count':len(v),'example':v[0]} for k,v in sorted(schemas.items())]},
 'existing_full_content_sha256_evidence':{'migration_hash_entries':len(hash_entries),'bounded_strict_receipts':len(receipt_entries),
   'union_entries':len(sha_union),'assigned_covered':len(sha_union&set(assigned)),'missing_assigned_sha_evidence':sorted(set(assigned)-sha_union),
   'extra_sha_evidence':sorted(sha_union-set(assigned)),'overlap_between_evidence_sets':len(set(hash_entries)&set(receipt_entries)),
   'invalid_sha256_values':sha_invalid,'size_mismatches_vs_canonical':sha_size_mismatch,'receipt_parse_errors':receipt_errors,
   'receipt_footer_row_mismatches':receipt_footer_mismatch,
   'method_note':'Reused prior full-file SHA-256 values; this final audit did not reread 359GB to recompute them.'},
 'claims':{'proves':['exact assigned filenames are present with canonical byte sizes','no extra formal Parquet or partial/temp remnants in the directory','all assigned Parquet footers are readable','schema uniformity and exact total footer rows','file size/mtime did not change during the audit','existing full-content SHA-256 evidence covers every assigned file'],
   'does_not_prove':['future storage media will never corrupt','semantic correctness of every value or decompression of every data page in the 1,348 hash-only files beyond prior hash provenance','completeness of any future/new Dewey dataset version','cross-region combined content unless Huazhong is audited separately']}
}
atomic_json(OUT,result); print(json.dumps({'status':result['status'],'out':str(OUT),'files':len(assigned),'rows':rows,'bytes':assigned_bytes,'schemas':len(schemas)},sort_keys=True))
if result['status']!='PASS': raise SystemExit(2)
