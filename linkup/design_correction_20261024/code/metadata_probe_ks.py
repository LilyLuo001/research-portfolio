"""Scheduled metadata-only probe; never reads Parquet data pages."""
import datetime
import glob
import importlib
import json
import os
import platform
import sys

ROOT = '/public/home/lilysharp/linkup_analysis_execution_oct02'
OUT = '/public/home/lilysharp/linkup_design_correction_20261024/results/KS_METADATA_PROBE_PUBLIC.json'
report = {'utc': datetime.datetime.utcnow().isoformat()+'Z', 'python': sys.version,
          'executable': sys.executable, 'host': platform.node(), 'slurm_job_id': os.environ.get('SLURM_JOB_ID'),
          'scope': 'Parquet footer/schema only; no row values, IDs or advertisement text read',
          'dependencies': {}, 'parents': [], 'fixed_keys': []}
for name in ('duckdb','pandas','pyarrow'):
    try:
        mod = importlib.import_module(name)
        report['dependencies'][name] = {'version': mod.__version__, 'module_file': mod.__file__}
    except Exception as exc:
        report['dependencies'][name] = {'error': str(exc)}
import pyarrow.parquet as pq

def footer(path):
    if not os.path.isfile(path):
        return {'path':path, 'exists':False}
    pf = pq.ParquetFile(path)
    return {'path':path, 'exists':True, 'bytes':os.path.getsize(path), 'rows':pf.metadata.num_rows,
            'row_groups':pf.metadata.num_row_groups, 'columns':[{'name':field.name,'type':str(field.type)} for field in pf.schema_arrow]}
for path in sorted(glob.glob(ROOT+'/private/comparison_join_v1/joined/*.parquet')):
    report['parents'].append(footer(path))
for path in (ROOT+'/private/next_stage_20261004/linkup/run-123660254/FIXED_RESEARCH_SAMPLE_KEYS_PRIVATE.parquet',
             ROOT+'/private/next_stage_20261004/linkup/run-123584403/FIXED_RESEARCH_SAMPLE_KEYS_PRIVATE.parquet'):
    report['fixed_keys'].append(footer(path))
report['parent_files'] = len(report['parents'])
report['parent_rows'] = sum(p['rows'] for p in report['parents'])
report['parent_schema_identical'] = len({json.dumps(p['columns'],sort_keys=True) for p in report['parents']}) == 1
os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,'w') as out:
    json.dump(report,out,indent=2,ensure_ascii=False)
print(json.dumps(report,indent=2,ensure_ascii=False))
