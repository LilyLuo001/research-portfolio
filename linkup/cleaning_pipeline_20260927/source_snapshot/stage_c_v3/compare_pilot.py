#!/usr/bin/env python3
"""Re-extract the frozen pilot and report measurement revisions, not accuracy."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
import sys


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''):h.update(b)
    return h.hexdigest()


def atomic_json(p,x):
    t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,ensure_ascii=False,default=str)+'\n');os.replace(str(t),str(p))


def worker(row):
    from requirement_candidates import extract
    try:
        x=extract(row['DESCRIPTION'])
        normalized=x['normalized_text']
        for e in x['evidence']:
            assert 0<=e['start']<=e['end']<=len(normalized), 'evidence offset out of range'
            assert normalized[e['snippet_start']:e['snippet_end']]==e['snippet'], 'snippet coordinate mismatch'
        if any(v['status']=='parse_error' for v in x['summary'].values()):
            return row['JOB_HASH'],x,'module_parse_error'
        return row['JOB_HASH'],x,None
    except Exception as e:
        return row['JOB_HASH'],None,type(e).__name__+': '+str(e)[:240]


def metrics(x,module):
    if x is None:return {'status':'parse_error','mention':False,'positive':False,'required':False,'preferred':False,'truncated':False}
    es=[e for e in x['evidence'] if e['module']==module]
    return {'status':x['summary'][module]['status'],
      'mention':x['summary'][module].get('candidate_count',0)>0,
      'positive':x['summary'][module].get('requirement_candidate_count',0)>0,
      'required':any(e.get('is_applicant_requirement') and e['context']=='required' for e in es),
      'preferred':any(e.get('is_applicant_requirement') and e['context']=='preferred' for e in es),
      'truncated':x.get('module_evidence_truncated',{}).get(module,False)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--sample',required=True);p.add_argument('--v1',required=True);p.add_argument('--out',required=True);p.add_argument('--workers',type=int,default=16)
    a=p.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq
    out=Path(a.out)
    identity={k:digest(v) for k,v in {'sample':a.sample,'v1_features':a.v1,'runner':__file__,'extractor':Path(__file__).with_name('requirement_candidates.py')}.items()}
    if out.exists():
        report_path=out/'report.json'
        if report_path.exists():
            old=json.loads(report_path.read_text())
            if old.get('identity')==identity and old.get('status')=='complete':
                print('Already complete, matching code/input hashes',flush=True);return
        raise RuntimeError('Refusing to reuse existing output without matching complete receipt; choose a new run directory')
    out.mkdir(parents=True)
    atomic_json(out/'identity.json',identity)
    n=pq.ParquetFile(a.sample).metadata.num_rows
    if n>30000:raise ValueError('bounded pilot only; limit 30000')
    rows=pq.read_table(a.sample).to_pylist()
    v1rows=pq.read_table(a.v1).to_pylist()
    v1={r['JOB_HASH']:json.loads(r['CANDIDATE_JSON']) for r in v1rows}
    assert len(v1)==len(v1rows)==n==len({r['JOB_HASH'] for r in rows})
    assert set(v1)==set(r['JOB_HASH'] for r in rows)
    workers=min(max(1,a.workers),int(os.environ.get('SLURM_CPUS_PER_TASK',a.workers)))
    started=time.time();outrows=[];changes=[];errors=[];agg=defaultdict(lambda:defaultdict(int));examples=[]
    examplekeys={'3c0ed2df5ae4ea3db2b22329d5027824','4ef5a6dcc909318b760ba93cbcc8ec7e','9c33e37f48b459e7bdf0800e199b0a37','f9923855fc00fe4032eb594030c24f21','b8e86280e9b15d1d3b6238e595c6f78a','65250db6bf22fcb0c98e7273d5d7a7e2','c6470b0b37988908ac6a9eebd3e9a056'}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for row, (key,x,error) in zip(rows,pool.map(worker,rows,chunksize=16)):
            assert key==row['JOB_HASH']
            if error:errors.append({'JOB_HASH':key,'error':error})
            outrows.append({'JOB_HASH':key,'SOURCE_FILE':row['SOURCE_FILE'],'SOURCE_ROW':row['SOURCE_ROW'],
              'COUNTRY_GROUP':row['COUNTRY_GROUP'],'COHORT':row['COHORT'],
              'RAW_SHA256':hashlib.sha256((row['DESCRIPTION'] or '').encode()).hexdigest(),
              'NORMALIZED_SHA256':hashlib.sha256(x['normalized_text'].encode()).hexdigest() if x else None,
              'STATUS':'parse_error' if error else 'unvalidated_candidate',
              'CANDIDATE_JSON':json.dumps(x,ensure_ascii=False)})
            for m in ('software','experience','education','tasks','ai'):
                old,new=metrics(v1[key],m),metrics(x,m)
                g=agg[(row['COUNTRY_GROUP'],row['COHORT'],m)];g['n']+=1
                c={'JOB_HASH':key,'COUNTRY_GROUP':row['COUNTRY_GROUP'],'COHORT':row['COHORT'],'MODULE':m,'OLD_STATUS':old['status'],'NEW_STATUS':new['status']}
                for field in ('mention','positive','required','preferred','truncated'):
                    c['OLD_'+field.upper()]=old[field];c['NEW_'+field.upper()]=new[field]
                    g['old_'+field]+=int(old[field]);g['new_'+field]+=int(new[field]);g['changed_'+field]+=int(old[field]!=new[field])
                g['parse_error']+=int(new['status']=='parse_error');changes.append(c)
            if key in examplekeys:
                examples.append({'JOB_HASH':key,'old_evidence':v1[key]['evidence'],'new_evidence':x['evidence'] if x else None,'interpretation':'targeted regression examples, not accuracy estimate'})
    def write(name,items):
        tmp=out/(name+'.tmp');t=pa.Table.from_pylist(items);pq.write_table(t,tmp,compression='zstd');assert pq.ParquetFile(tmp).metadata.num_rows==len(items);os.replace(str(tmp),str(out/name))
    write('candidate_features_v3.parquet',outrows)
    write('ad_module_changes.parquet',changes)
    summary=[dict(COUNTRY_GROUP=k[0],COHORT=k[1],MODULE=k[2],**dict(v)) for k,v in sorted(agg.items())]
    write('cohort_module_diagnostics.parquet',summary)
    atomic_json(out/'targeted_regressions.json',examples);atomic_json(out/'parse_errors.json',errors)
    total=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
    if total>1_000_000_000:raise RuntimeError('pilot output exceeds 1GB cap')
    assert len(outrows)==n and len(changes)==5*n
    report={'status':'complete' if not errors else 'complete_with_errors','identity':identity,'sample_rows':n,'candidate_rows':len(outrows),'ad_module_rows':len(changes),'parse_error_rows':len(errors),'targeted_cases_found':len(examples),'output_bytes':total,'elapsed_seconds':time.time()-started,'workers':workers,'input_scope':'fixed regional stratified pilot; not population prevalence','accuracy_estimated':False,'human_validation_status':'pending','change_interpretation':'v2-v3 candidate differences, not precision/recall or economic effects','raw_data_changed':False}
    atomic_json(out/'report.json',report)
    print(json.dumps(report,indent=2),flush=True)
    if errors:sys.exit(2)

if __name__=='__main__':main()
