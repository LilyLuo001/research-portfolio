#!/usr/bin/env python3
"""Scheduled metadata-only projection for the authorized SCNet correction."""
import hashlib
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
import pyarrow.parquet as pq

ROOT = Path('/work/home/lilysharp/private/design_correction_20261024')
BASE = Path('/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private')
FIXED = Path('/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/verified_fixed10000/MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet')
FILES = {
    'REFERENCE_AD_LEVEL_PRIVATE.parquet': BASE / 'empirical_20261024/private/AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet',
    'EMPIRICAL_RECEIPT_PUBLIC.json': BASE / 'empirical_20261024/public/RUN_RECEIPT_PUBLIC.json',
    'ISOLATION_PRIVATE.jsonl': BASE / 'continuation/isolation/BLOCKED_CONTEXTS_PRIVATE.jsonl',
    'cell_allocation.csv': Path('/work/home/lilysharp/private/formal800_20261012/weight_lineage_20261012/input/cell_allocation.csv'),
}

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def main():
    if not os.environ.get('SLURM_JOB_ID'): raise RuntimeError('scheduler required')
    out = ROOT / 'handoff_private'
    if (out / 'HANDOFF_PUBLIC.json').exists(): raise RuntimeError('completed handoff guard')
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    if sha(FIXED) != 'e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35':
        raise RuntimeError('fixed input changed')
    cols = ['JOB_HASH','SOURCE_FILE','SOURCE_ROW','RECORD_SOURCE_ROW','OCCUPATION_MAJOR','CENSUS_REGION','created_year','arm','total_inclusion_probability','nested_design_weight','original_inclusion_probability','conditional_inclusion_probability']
    table = pq.read_table(FIXED, columns=cols)
    if table.num_rows != 10000: raise RuntimeError('not complete fixed10k')
    pq.write_table(table, out / 'FIXED_KEYS_WEIGHTS_PRIVATE.parquet', compression='zstd')
    ref = FILES['REFERENCE_AD_LEVEL_PRIVATE.parquet']
    receipt = json.loads(FILES['EMPIRICAL_RECEIPT_PUBLIC.json'].read_text())
    if receipt.get('status') != 'pass' or sha(ref) != receipt['private_output']['sha256']:
        raise RuntimeError('reference not accepted empirical output')
    if sha(FILES['cell_allocation.csv']) != 'bad5965d982ddb3f81efa43ccca52e14b34684458976370e2dbe4a3949f77ca9':
        raise RuntimeError('allocation changed')
    for name, src in FILES.items(): shutil.copyfile(src, out/name)
    for p in out.iterdir(): os.chmod(p, 0o600)
    report = {'created_utc':datetime.now(timezone.utc).isoformat(), 'job_id':os.environ['SLURM_JOB_ID'], 'purpose':'Metadata-only unchanged10000-ad projection and verified reference transport; no sampling or text extraction', 'rows':table.num_rows, 'fixed_columns':cols, 'reference_columns':pq.ParquetFile(ref).schema_arrow.names, 'fixed_source_sha256':sha(FIXED), 'outputs':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()}, 'code_sha256':sha(__file__), 'status':'pass'}
    (out/'HANDOFF_PUBLIC.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'public').mkdir(exist_ok=True)
    shutil.copyfile(out/'HANDOFF_PUBLIC.json',ROOT/'public/HANDOFF_PUBLIC.json')

if __name__ == '__main__': main()
