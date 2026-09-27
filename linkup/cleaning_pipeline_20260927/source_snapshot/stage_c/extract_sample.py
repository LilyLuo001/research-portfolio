#!/usr/bin/env python3
"""Offline candidate extraction for a bounded, already-selected validation sample.
No promotion to validated indicators; raw evidence is retained in the sample.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


def atomic_json(path, obj):
    tmp = Path(str(path) + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + '\n')
    os.replace(str(tmp), str(path))


def extract_row(row):
    from requirement_candidates import extract
    text = row.get('DESCRIPTION')
    key = {k: row.get(k) for k in ('JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW')}
    try:
        result = extract(text)
        json.dumps(result, ensure_ascii=False)
        status = 'parse_error' if any(v.get('status') == 'parse_error' for v in result.get('summary', {}).values()) else 'unvalidated_candidate'
        return dict(key, candidate_result=result, status=status)
    except Exception as e:
        return dict(key, candidate_result=None, status='parse_error',
                    error_type=type(e).__name__, error=str(e)[:300])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sample', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--workers', type=int, default=16)
    a = p.parse_args()
    import pyarrow as pa
    import pyarrow.parquet as pq
    src, out = Path(a.sample), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    run_paths=[Path(__file__), Path(__file__).with_name('requirement_candidates.py')]
    code_sha=hashlib.sha256(b''.join(x.read_bytes() for x in run_paths)).hexdigest()
    sample_sha=hashlib.sha256(src.read_bytes()).hexdigest()
    identity={'sample_sha256':sample_sha,'code_sha256':code_sha}
    mark=out/'candidate_report.json'
    if mark.exists():
        old=json.loads(mark.read_text())
        if old.get('identity') == identity and old.get('status')=='complete':
            assert all((out/x).is_file() for x in ('candidates.jsonl','candidate_features.parquet'))
            print('matching completed candidate run exists',flush=True)
            return
        raise RuntimeError('Output belongs to a different or incomplete run; choose a new --out')
    pf=pq.ParquetFile(src)
    if pf.metadata.num_rows > 30000:
        raise RuntimeError('Pilot input exceeds 30,000 ads; not a full-corpus extractor')
    if 'DESCRIPTION' not in pf.schema_arrow.names:
        raise ValueError('sample must retain DESCRIPTION')
    rows=pq.read_table(src).to_pylist()
    if len({r['JOB_HASH'] for r in rows}) != len(rows):
        raise ValueError('sample contains duplicate JOB_HASH')
    max_workers=min(max(1,a.workers), int(os.environ.get('SLURM_CPUS_PER_TASK',a.workers)))
    started=time.time()
    tmp=out/'candidates.jsonl.tmp'
    failures=[]; features=[]
    with tmp.open('w') as f, cf.ProcessPoolExecutor(max_workers=max_workers) as pool:
        for item in pool.map(extract_row, rows, chunksize=16):
            f.write(json.dumps(item, ensure_ascii=False)+'\n')
            if item['status']=='parse_error': failures.append({k:v for k,v in item.items() if k!='candidate_result'})
            features.append({'JOB_HASH':item['JOB_HASH'], 'SOURCE_FILE':item['SOURCE_FILE'],
                             'SOURCE_ROW':item['SOURCE_ROW'], 'STATUS':item['status'],
                             'CANDIDATE_JSON':json.dumps(item['candidate_result'],ensure_ascii=False)})
        f.flush();os.fsync(f.fileno())
    if tmp.stat().st_size > 500_000_000:
        raise RuntimeError('Evidence output exceeds 500MB pilot budget')
    os.replace(str(tmp),str(out/'candidates.jsonl'))
    schema=pa.schema([('JOB_HASH',pa.string()),('SOURCE_FILE',pa.string()),('SOURCE_ROW',pa.int64()),
                      ('STATUS',pa.string()),('CANDIDATE_JSON',pa.string())])
    ft=out/'candidate_features.parquet.tmp'
    pq.write_table(pa.Table.from_pylist(features,schema=schema),ft,compression='zstd')
    assert pq.ParquetFile(ft).metadata.num_rows==len(rows)
    os.replace(str(ft),str(out/'candidate_features.parquet'))
    atomic_json(out/'failures.json',failures)
    atomic_json(mark,{'identity':identity,'status':'complete' if not failures else 'complete_with_errors',
                'input_rows':len(rows),'output_rows':len(features),'parse_errors':len(failures),
                'seconds':time.time()-started,'workers':max_workers,'validated_economic_features':False,
                'scope':'regional file-sampled, time-stratified pilot; not population estimates',
                'next_gate':'human development and independent held-out validation by period',
                'sample_file':str(src)})
    print(mark.read_text(),flush=True)
    if failures:sys.exit(2)

if __name__=='__main__':
    main()
