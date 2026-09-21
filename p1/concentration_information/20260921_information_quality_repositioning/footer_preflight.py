"""Read-only, bounded source-name and Parquet-footer audit; never reads columns/rows.

Run on SCC using stdin. Output is schema/partition metadata only. No footer column
statistics, financial values, identifiers, credentials, or raw rows are emitted.
"""
import datetime
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path('/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw')
PATTERNS = {
    'quarterly_fundamentals': ['*fundq*.parquet'],
    'annual_fundamentals': ['*funda*.parquet'],
    'ccm_link': ['*ccm*.parquet'],
    'detail_eps_direct': ['ibes_detu_eps_*.parquet'],
    'actual_eps_direct': ['ibes_actuals_eps_*.parquet'],
}
DIRECTORIES = [ROOT, ROOT / 'maximal', ROOT / 'rescue', ROOT / 'rescue_remaining']
RELEVANT = set('gvkey datadate fyearq fqtr fyr rdq ibq atq saleq epspxq ajexq indfmt datafmt consol popsrc pdateq fdateq finalq updq linkdt linkenddt linktype linkprim lpermno lpermco permno permco ticker cusip fpedats pends analys estimator anndats anntims actdats acttims measure pdicity fpi value actual usfirm curr curcode'.split())

def main():
    result = {'scope': 'BOUNDED_NONRECURSIVE_FILE_AND_FOOTER_ONLY',
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'raw_rows_read': False, 'column_statistics_read': False,
              'directory_scope': [str(d) for d in DIRECTORIES], 'families': {}}
    for family, patterns in PATTERNS.items():
        paths = sorted({p for d in DIRECTORIES if d.is_dir()
                        for pattern in patterns for p in d.glob(pattern) if p.is_file()})
        schemas = {}
        files = []
        for path in paths:
            try:
                pf = pq.ParquetFile(path)
                schema = [(f.name, str(f.type)) for f in pf.schema_arrow if f.name.lower() in RELEVANT]
                key = json.dumps(schema)
                sid = schemas.setdefault(key, {'schema_id': len(schemas) + 1, 'relevant_fields': schema})['schema_id']
                files.append({'path': str(path.relative_to(ROOT)), 'schema_id': sid,
                              'physical_rows': pf.metadata.num_rows, 'size_bytes': path.stat().st_size})
            except Exception as exc:
                files.append({'path': str(path.relative_to(ROOT)), 'error_type': type(exc).__name__})
        result['families'][family] = {'patterns': patterns, 'matched_files': len(paths),
                                     'schemas': list(schemas.values()), 'files': files}
    result['warning'] = ('Filename years and footer rows are not economic-date coverage or unique observations. '
                         'No-match is absence within this bounded name search, not archive-wide absence. '
                         'No source versions pooled. Forecast/actual value comparability and point-in-time vintages NOT_VERIFIED.')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
