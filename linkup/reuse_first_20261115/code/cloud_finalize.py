"""Wait a bounded interval, compare frozen outputs, and archive this finite run."""
import datetime,hashlib,importlib.util,json,os,sys,tarfile,time
from pathlib import Path
R=Path.home()/'migration';D=R/'reuse_first_20261115/run01/benchmark20'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
end=time.time()+900
while time.time()<end:
    state=read(D/'RUN_STATUS_PUBLIC.json')
    if state['status']!='running':break
    time.sleep(20)
assert state['status']=='finite_benchmark_completed','finite_run_not_completed_no_comparison'
spec=importlib.util.spec_from_file_location('comparison',D/'cloud_compare_benchmark.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
report=module.compare(R)
archive=D.parent/'BENCHMARK20_EVIDENCE_PRIVATE.tar.gz'
if not archive.exists():
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(D.rglob('*')):
            if p.is_file() and p.name not in ('WORKER.lock','WORKER.log'):tar.add(p,arcname=str(p.relative_to(D)),recursive=False)
sys.path.insert(0,str(R/'code'))
from checkpoint_scope import upload,BASE
from workflow import call
key='reuse-first/20261115/benchmark20/BENCHMARK20_EVIDENCE_PRIVATE.tar.gz'
receipt=upload(archive,key)
with call(BASE+key,'https://storage.azure.com/',headers={'x-ms-version':'2023-11-03'}) as response:
    h=hashlib.sha256()
    while True:
        block=response.read(1048576)
        if not block:break
        h.update(block)
assert h.hexdigest()==sha(archive)==receipt['sha256'],'archive_readback_sha_mismatch'
summary={'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':state,'relative_comparison':{'engineering_pass_records':report['engineering_pass_records'],'paired_review_records':report['comparison_coverage']['paired_review_records'],'new_unknown_records':report['comparison_coverage']['candidate_records_with_enum_unknown'],'full_business_exact_records':report['full_business_structure_exact_records_among_paired'],'full_business_without_quotes_exact_records':report['full_business_without_quotes_exact_records_among_paired'],'categorical_exact':{k:{'paired':v['paired'],'exact':v['exact']} for k,v in report['categorical_exact_agreement'].items()}},'full_comparison_sha256':sha(D/'comparison_v1/COMPARISON_PUBLIC.json'),'input_sha256':sha(D/'INPUTS_PRIVATE.jsonl'),'worker_sha256':sha(D/'cloud_benchmark_worker.py'),'archive':{'bytes':archive.stat().st_size,'sha256':sha(archive),'blob_key':key,'readback_sha256_verified':True},'quality_certified':False,'new_production_accepted':0,'limits':'Fixed known-full candidate subset; Kimi comparison is not ground truth; no population accuracy or full-corpus cost extrapolation.'}
(D/'FINAL_SUMMARY_PUBLIC.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,separators=(',',':')))
