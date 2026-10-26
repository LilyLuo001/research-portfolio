#!/usr/bin/env python3
"""Scheduled schema/provenance inventory only; no row values or body output."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def shape(x):
    if isinstance(x, dict):
        return {k: shape(v) for k, v in x.items()}
    if isinstance(x, list):
        return {'type': 'list', 'first_item_shape': shape(x[0]) if x else None}
    return type(x).__name__


def inspect(p):
    r = {'path': str(p), 'exists': p.is_file()}
    if not r['exists']:
        return r
    r['bytes'] = p.stat().st_size
    if p.suffix == '.parquet':
        try:
            import pyarrow.parquet as pq
            f = pq.ParquetFile(p)
            r.update(rows=f.metadata.num_rows, columns=[{'name': x.name, 'type': str(x.type)} for x in f.schema_arrow])
        except ImportError:
            r['dependency_missing'] = 'pyarrow'
    elif p.suffix in ('.json', '.jsonl'):
        if p.suffix == '.jsonl':
            with p.open() as f:
                first = next((json.loads(z) for z in f if z.strip()), {})
            r['first_record_shape'] = shape(first)
        else:
            obj = json.loads(p.read_text())
            r['top_level_shape'] = shape(obj)
        r['sha256'] = sha(p)
    return r


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--mode', choices=('ks', 'wz'), required=True)
    a.add_argument('--output', required=True)
    v = a.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled_job_required')
    if v.mode == 'ks':
        paths = [
            '/public/home/lilysharp/linkup_metadata_research_20261026/run001/private/AD_LEVEL_RESEARCH_PRIVATE.parquet',
            '/public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl',
            '/public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1/CORPUS_RELEASE_VIEWS_PRIVATE.sql',
            '/public/home/lilysharp/linkup_analysis_execution_oct02/private/gate_v2_20261003/ALL_REGIONS_VERIFIED_COMPLETE.json']
        base = Path('/public/home/lilysharp/linkup_analysis_execution_oct02/private/semantic_narrow_v1')
        paths += [str(x) for x in sorted(base.glob('*.parquet'))[:2]]
    else:
        root = '/work/home/lilysharp/private/'
        paths = [root + x for x in (
            'relation_channel_20261025/reviews_v1/snapshots/47393594/REVIEW_LEDGER_PRIVATE.jsonl',
            'relation_channel_20261025/pro_packets_v1/CANDIDATE_PACKET_MAP_PRIVATE.jsonl',
            'year_object_relation_20261024/inputs_v1/CANDIDATES_PRIVATE.jsonl',
            'year_object_relation_20261024/inputs_v1/CONTEXT_STATES_PRIVATE.jsonl',
            'linkup_relation_feasibility_20261024/INPUT_MANIFEST_PRIVATE.json',
            'fixed10k_semantic_production_20261017/private/empirical_20261024/private/AD_LEVEL_JOINED_ANALYSIS_PRIVATE.parquet')]
    report = {'mode': v.mode, 'job': os.environ['SLURM_JOB_ID'],
              'no_body_or_row_values_emitted': True,
              'sources': [inspect(Path(x)) for x in paths]}
    out = Path(v.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
