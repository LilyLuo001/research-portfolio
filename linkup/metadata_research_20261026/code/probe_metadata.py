#!/usr/bin/env python3
"""Scheduled, footer-only metadata binding. No advertisement column values."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

def main():
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled SCNet execution required')
    import duckdb
    import pandas
    import pyarrow.parquet as pq
    root = Path('/public/home/lilysharp/linkup_metadata_research_20261026')
    out = root / 'probe001/public'
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'METADATA_PROBE_PUBLIC.json'
    if target.exists():
        raise RuntimeError('completed probe guard')
    bridge = Path('/public/home/lilysharp/linkup_design_correction_20261024/run001/private/AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet')
    parents = sorted(Path('/public/home/lilysharp/linkup_analysis_execution_oct02/private/comparison_join_v1/joined').glob('[0-9a-f].parquet'))
    index_root = Path('/public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1')
    records = sorted(index_root.glob('hash_prefix=*/*.parquet'))
    def footer(path):
        p = pq.ParquetFile(path)
        return {'path':str(path),'bytes':path.stat().st_size,'rows':p.metadata.num_rows,
                'columns':[{'name':f.name,'type':str(f.type)} for f in p.schema_arrow]}
    result = {'job':os.environ['SLURM_JOB_ID'],'created_utc':datetime.now(timezone.utc).isoformat(),
              'mode':'footer-only; no column values or semantic labels read',
              'bridge':footer(bridge),'candidate_join':[footer(p) for p in parents],
              'records_index':{'root':str(index_root),'files':len(records),
                               'first_footer':footer(records[0]) if records else None},
              'runtime':{'duckdb':duckdb.__version__,'pandas':pandas.__version__},
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with target.open('x') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'status':'completed_metadata_probe','job':os.environ['SLURM_JOB_ID'],
                      'candidate_join_files':len(parents),'records_index_files':len(records)}))

if __name__ == '__main__':
    main()
