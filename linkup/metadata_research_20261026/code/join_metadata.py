#!/usr/bin/env python3
"""Scheduled, bounded metadata extension of the immutable accepted fixed10k bridge.

Only whitelisted nonsemantic columns are projected from lookup sources. Original
bridge columns are retained as Arrow arrays, without pandas round trips.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

KEY = ['JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW']
RKEY = ['JOB_HASH', 'RECORD_SOURCE_ROW']
FIELDS = ['COMPANY_ID', 'TITLE', 'COUNTRY', 'STATE', 'CENSUS_REGION', 'CREATED',
          'LAST_CHECKED', 'LAST_UPDATED', 'DELETE_DATE', 'CROSSES_2022_11_30',
          'OBSERVATION_END', 'OBSERVATION_CLOSED', 'DATE_COMPLETE',
          'STALE_DELETE_OR_REAPPEARANCE']
DATES = {'CREATED', 'LAST_CHECKED', 'LAST_UPDATED', 'DELETE_DATE', 'OBSERVATION_END'}
FLAGS = {'CROSSES_2022_11_30', 'OBSERVATION_CLOSED', 'DATE_COMPLETE',
         'STALE_DELETE_OR_REAPPEARANCE'}
VERSION = 'fixed10k-bounded-metadata-extension-v1'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def qi(value):
    return '"' + value.replace('"', '""') + '"'


def qs(value):
    return "'" + str(value).replace("'", "''") + "'"


def key(row, columns):
    values = tuple(row[x] for x in columns)
    if any(x is None for x in values):
        raise RuntimeError('null canonical lookup key')
    return tuple(int(v) if x in {'SOURCE_ROW', 'RECORD_SOURCE_ROW'} else str(v)
                 for x, v in zip(columns, values))


def source_info(path, columns):
    f = pq.ParquetFile(path)
    return {'name': path.name, 'bytes': path.stat().st_size,
            'footer_rows': f.metadata.num_rows,
            'projected_columns': columns,
            'schema': [{'name': x.name, 'type': str(x.type)} for x in f.schema_arrow]}


def bounded_lookup(con, paths, keys_table, columns, key_columns, source_label):
    """Count every matching source row before allowing any metadata value."""
    results = {}
    provenance = []
    key_name = 'requested_' + source_label
    con.register(key_name, keys_table)
    # Group by exact footer schema for compatible union scans. This avoids one
    # SQL query per physical Records file while retaining every duplicate row.
    groups = {}
    for path in paths:
        available = set(pq.ParquetFile(path).schema_arrow.names)
        if not set(key_columns) <= available:
            raise RuntimeError(source_label + ' lacks exact lookup columns')
        projected = key_columns + [x for x in columns if x in available and x not in key_columns]
        provenance.append(source_info(path, projected))
        groups.setdefault(tuple(projected), []).append(path)
    for projected, group_paths in groups.items():
        file_list = '[' + ','.join(qs(path) for path in group_paths) + ']'
        sql = ('SELECT ' + ','.join('r.' + qi(x) for x in projected) +
               (',r.filename AS __index_filename' if source_label == 'records' else '') +
               ' FROM read_parquet(' + file_list + ',union_by_name=true' +
               (',filename=true' if source_label == 'records' else '') + ') r SEMI JOIN ' + key_name +
               ' k USING (' + ','.join(map(qi, key_columns)) + ')')
        # The result is restricted to the original fixed10k keys, never a corpus join.
        for row in con.execute(sql).fetch_arrow_table().to_pylist():
            k = key(row, key_columns)
            if k in results:
                results[k]['count'] += 1
                results[k]['row'] = None
            else:
                results[k] = {'count': 1, 'row': row}
    con.unregister(key_name)
    return results, provenance


def normalized(field, value):
    if value is None:
        return None
    if field in DATES:
        # DuckDB applies the same cast to all source timestamp units.
        return value
    if field in FLAGS:
        return bool(value)
    return str(value)


def state(count):
    return 'match0' if count == 0 else 'match1' if count == 1 else 'match_gt1'


def recover_titles(records, index_root, raw_root):
    """Resolve only unique index rows to original per-file offsets and row groups.

    A manifest binds each index partition filename to its original raw file.
    No JOB_HASH search or whole raw-table join is performed.
    """
    core = ['JOB_HASH', 'COMPANY_ID', 'COUNTRY', 'STATE', 'CREATED',
            'LAST_UPDATED', 'LAST_CHECKED', 'DELETE_DATE']
    manifests = {}
    for path in sorted((index_root / 'source_manifests').glob('*.json')):
        try:
            value = json.loads(path.read_text())
            if value.get('status') != 'complete':
                continue
            for output in value.get('outputs', []):
                bound = (index_root / output['path']).resolve()
                manifests.setdefault(str(bound), []).append((path, value, output))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    results, grouped, inventory = {}, {}, []
    for k, entry in records.items():
        if entry['count'] != 1:
            results[k] = {'status': 'raw_title_index_ambiguous'}
            continue
        row = entry['row']
        filename = row.get('__index_filename')
        bindings = manifests.get(str(Path(filename).resolve()), []) if filename else []
        if len(bindings) != 1:
            results[k] = {'status': 'raw_title_manifest_unavailable_or_ambiguous'}
            continue
        mp, manifest, output = bindings[0]
        source = manifest.get('source', {})
        source_name = source.get('file', '')
        if not source_name or Path(source_name).name != source_name or Path(filename).name != source_name:
            results[k] = {'status': 'raw_title_source_mapping_invalid'}
            continue
        grouped.setdefault(source_name, []).append((k, row, mp, manifest, output))
    for source_name, requests in grouped.items():
        raw = raw_root / source_name
        try:
            bindings = {(str(x[2]), json.dumps(x[3]['source'], sort_keys=True)) for x in requests}
            if len(bindings) != 1:
                raise ValueError('source_manifest_conflict')
            mp, manifest = requests[0][2], requests[0][3]
            source = manifest['source']
            pf = pq.ParquetFile(raw)
            skinny = pa.schema([pf.schema_arrow.field(name) for name in core])
            skinny_sha = hashlib.sha256(str(skinny).encode()).hexdigest()
            if raw.stat().st_size != source['bytes'] or pf.metadata.num_rows != source['footer_rows'] or skinny_sha != source['skinny_schema_sha256']:
                raise ValueError('raw_source_fingerprint_mismatch')
            if 'TITLE' not in pf.schema_arrow.names:
                raise ValueError('raw_title_column_unavailable')
            checked_index_files = set()
            for _, row, _, _, output in requests:
                index_file = Path(row['__index_filename'])
                if str(index_file) in checked_index_files:
                    continue
                if index_file.stat().st_size != output['bytes'] or pq.ParquetFile(index_file).metadata.num_rows != output['rows']:
                    raise ValueError('index_output_manifest_mismatch')
                checked_index_files.add(str(index_file))
            offsets = [0]
            for rg in range(pf.metadata.num_row_groups):
                offsets.append(offsets[-1] + pf.metadata.row_group(rg).num_rows)
            import bisect
            by_group = {}
            for k, row, _, _, _ in requests:
                offset = int(row['RECORD_SOURCE_ROW'])
                if offset < 0 or offset >= pf.metadata.num_rows:
                    results[k] = {'status': 'raw_title_offset_out_of_range'}
                    continue
                rg = bisect.bisect_right(offsets, offset) - 1
                by_group.setdefault(rg, []).append((k, row, offset - offsets[rg]))
            checked = 0
            for rg, selected in by_group.items():
                table = pf.read_row_group(rg, columns=core + ['TITLE'])
                # Select just requested positions before Python materialization.
                selected_rows = table.take(pa.array([x[2] for x in selected], type=pa.int64())).to_pylist()
                for (k, index_row, _), raw_row in zip(selected, selected_rows):
                    agreement = all(normalized(field, raw_row.get(field)) == normalized(field, index_row.get(field)) for field in core)
                    if not agreement:
                        results[k] = {'status': 'raw_row_conflict'}
                    else:
                        title = raw_row['TITLE']
                        results[k] = {'status': 'verified_exact_raw_row', 'title': None if title is None else str(title)}
                    checked += 1
            inventory.append({'source_file': source_name, 'bytes': raw.stat().st_size,
                              'footer_rows': pf.metadata.num_rows,
                              'skinny_schema_sha256': skinny_sha,
                              'source_manifest_sha256': sha(mp),
                              'mtime_matches_manifest': raw.stat().st_mtime_ns == source.get('mtime_ns'),
                              'selected_rows_checked': checked,
                              'selected_row_groups_read': len(by_group),
                              'projected_columns': core + ['TITLE']})
        except (OSError, ValueError, KeyError, TypeError, pa.ArrowException) as exc:
            safe_reasons = {'source_manifest_conflict', 'raw_source_fingerprint_mismatch',
                            'raw_title_column_unavailable', 'index_output_manifest_mismatch'}
            reason = str(exc) if isinstance(exc, ValueError) and str(exc) in safe_reasons else type(exc).__name__
            for k, _, _, _, _ in requests:
                results[k] = {'status': 'raw_title_source_verification_unavailable', 'reason': reason}
    builder = index_root.parent / 'scripts' / 'build_records_index.py'
    return results, {'enabled': True, 'method': 'manifest-bound original per-file RECORD_SOURCE_ROW offsets; selected raw row groups only',
                     'unique_records_key_status_counts': dict(Counter(x['status'] for x in results.values())),
                     'verification_failure_reason_counts': dict(Counter(x['reason'] for x in results.values() if 'reason' in x)),
                     'source_provenance': inventory,
                     'original_index_builder_sha256': sha(builder) if builder.is_file() else None,
                     'full_raw_file_sha256_verified': False,
                     'verification_scope': 'manifest source bytes/footer/skinny schema and selected-row exact core-field agreement; no full raw hash claim'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('bridge', 'bridge-receipt', 'candidate-dir', 'records-index',
                 'private-output', 'public-output'):
        ap.add_argument('--' + name, required=True)
    ap.add_argument('--raw-records-dir')
    a = ap.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled SCNet job required')
    allocated_cpus = int(os.environ.get('SLURM_CPUS_PER_TASK', '4'))
    pa.set_cpu_count(allocated_cpus)
    private = Path(a.private_output)
    public = Path(a.public_output)
    if not any(x in {'private', 'private_output', 'private-output'} or 'private' in x
               for x in private.parts):
        raise RuntimeError('private output path required')
    private.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    receipt_path = public / 'METADATA_JOIN_RECEIPT_PUBLIC.json'
    dest = private / 'AD_LEVEL_RESEARCH_PRIVATE.parquet'
    if receipt_path.exists() or dest.exists():
        raise RuntimeError('completed or existing output guard')
    complete_marker = Path(a.records_index) / 'COMPLETE'
    records_complete = {'status': 'available', 'sha256': sha(complete_marker)} if complete_marker.is_file() else {
        'status': 'unavailable', 'sha256': None,
        'fallback_provenance': 'all existing source files footer/schema inventoried before lookup'}
    receipt = json.loads(Path(a.bridge_receipt).read_text())
    bridge_sha = sha(a.bridge)
    if receipt.get('status') != 'pass' or receipt.get('private_bridge', {}).get('sha256') != bridge_sha:
        raise RuntimeError('bridge not bound to accepted design receipt')
    original = pq.read_table(a.bridge)
    if original.num_rows != 10000 or any(x.startswith('metadata_') for x in original.column_names):
        raise RuntimeError('expected untouched fixed10000 bridge')
    # These are existing narrow labels and metadata; no description/quote is admitted.
    forbidden = {'DESCRIPTION', 'JOB_DESCRIPTION', 'TEXT', 'RAW_TEXT', 'EVIDENCE_QUOTE'}
    if any(x.upper() in forbidden for x in original.column_names):
        raise RuntimeError('unexpected text column in accepted bridge')
    rows = original.select(KEY).to_pylist()
    canonical = [key(x, KEY) for x in rows]
    if len(set(canonical)) != 10000:
        raise RuntimeError('duplicate canonical bridge keys')
    prefixes = sorted({k[0][0].lower() for k in canonical})
    if any(not re.fullmatch('[0-9a-f]', x) for x in prefixes):
        raise RuntimeError('invalid original hash prefix')
    candidate_paths = [Path(a.candidate_dir) / (p + '.parquet') for p in prefixes]
    index_paths = []
    for p in prefixes:
        parts = sorted((Path(a.records_index) / ('hash_prefix=' + p)).glob('*.parquet'))
        if not parts:
            raise RuntimeError('missing existing Records index partition')
        index_paths.extend(parts)
    con = duckdb.connect()
    con.execute('SET threads=' + str(allocated_cpus))
    con.execute("SET memory_limit='8GB'")
    con.execute('SET temp_directory=' + qs(private / 'duckdb_tmp'))
    ckeys = original.select(KEY)
    # Repeated Records keys across different advertisements are intentional reuse.
    record_dict = {key(r, RKEY): {x: r[x] for x in RKEY} for r in rows}
    rkeys = pa.Table.from_pylist(list(record_dict.values()))
    candidate, cp = bounded_lookup(con, candidate_paths, ckeys, FIELDS, KEY, 'candidate')
    records, rp = bounded_lookup(con, index_paths, rkeys, FIELDS, RKEY, 'records')
    raw_titles, raw_report = recover_titles(records, Path(a.records_index), Path(a.raw_records_dir)) if a.raw_records_dir else ({}, {'enabled': False})
    added = {x: [] for x in FIELDS}
    sources = {x: Counter() for x in FIELDS}
    field_states = {x: [] for x in FIELDS}
    candidate_counts, records_counts, conflicts = [], [], []
    cstates, rstates, company_valid = [], [], []
    bridge_regions = original['CENSUS_REGION'].to_pylist() if 'CENSUS_REGION' in original.column_names else [None] * 10000
    bridge_years = original['created_year'].to_pylist() if 'created_year' in original.column_names else [None] * 10000
    for ordinal, row in enumerate(rows):
        ce = candidate.get(key(row, KEY), {'count': 0, 'row': None})
        re_ = records.get(key(row, RKEY), {'count': 0, 'row': None})
        candidate_counts.append(ce['count']); records_counts.append(re_['count'])
        cstates.append(state(ce['count'])); rstates.append(state(re_['count']))
        cr, rr = ce['row'] or {}, re_['row'] or {}
        bad = []
        for field in FIELDS:
            cv, rv = normalized(field, cr.get(field)), normalized(field, rr.get(field))
            # Any duplicate source match makes that source unavailable, including identical duplicates.
            if cv is not None and rv is not None and cv != rv:
                value, provenance = None, 'cross_source_conflict'
                bad.append(field)
            elif cv is not None:
                value, provenance = cv, 'candidate_exact_ad_key'
            elif rv is not None:
                value, provenance = rv, 'records_exact_hash_row'
            else:
                value, provenance = None, 'unavailable'
            if field == 'CENSUS_REGION' and value is not None and bridge_regions[ordinal] is not None and str(value) != str(bridge_regions[ordinal]):
                value, provenance = None, 'bridge_conflict'; bad.append(field)
            if field == 'CREATED' and value is not None and bridge_years[ordinal] is not None and value.year != int(bridge_years[ordinal]):
                value, provenance = None, 'bridge_conflict'; bad.append(field)
            added[field].append(value)
            sources[field][provenance] += 1
            field_states[field].append(provenance)
        title_result = raw_titles.get(key(row, RKEY))
        if title_result and title_result['status'] == 'verified_exact_raw_row':
            if added['TITLE'][-1] is None:
                sources['TITLE'][field_states['TITLE'][-1]] -= 1
                added['TITLE'][-1] = title_result['title']
                field_states['TITLE'][-1] = 'verified_exact_raw_row' if title_result['title'] is not None else 'verified_raw_title_missing'
                sources['TITLE'][field_states['TITLE'][-1]] += 1
            elif added['TITLE'][-1] != title_result['title']:
                sources['TITLE'][field_states['TITLE'][-1]] -= 1
                added['TITLE'][-1] = None
                field_states['TITLE'][-1] = 'raw_title_conflict'
                sources['TITLE']['raw_title_conflict'] += 1
                bad.append('TITLE')
        elif title_result:
            if added['TITLE'][-1] is None:
                sources['TITLE'][field_states['TITLE'][-1]] -= 1
                field_states['TITLE'][-1] = title_result['status']
                sources['TITLE'][title_result['status']] += 1
            if title_result['status'] == 'raw_row_conflict':
                bad.append('RAW_ROW_FINGERPRINT')
        conflicts.append('|'.join(sorted(set(bad))))
        company_valid.append(added['COMPANY_ID'][-1] is not None and
                             ce['count'] <= 1 and re_['count'] <= 1 and not bad)
    out = original
    for field in FIELDS:
        dtype = pa.timestamp('us') if field in DATES else pa.bool_() if field in FLAGS else pa.string()
        out = out.append_column('metadata_' + field.lower(), pa.array(added[field], type=dtype))
        out = out.append_column('metadata_' + field.lower() + '_state',
                                pa.array(field_states[field], type=pa.string()))
    for name, values, dtype in (
        ('metadata_candidate_matches', candidate_counts, pa.int64()),
        ('metadata_records_matches', records_counts, pa.int64()),
        ('metadata_candidate_match_state', cstates, pa.string()),
        ('metadata_records_match_state', rstates, pa.string()),
        ('metadata_conflict_fields', conflicts, pa.string()),
        ('metadata_conflict', [bool(x) for x in conflicts], pa.bool_()),
        ('metadata_company_valid', company_valid, pa.bool_())):
        out = out.append_column(name, pa.array(values, type=dtype))
    if not out.select(original.column_names).equals(original):
        raise RuntimeError('original bridge columns changed before write')
    temporary = private / 'AD_LEVEL_RESEARCH_PRIVATE.parquet.tmp'
    pq.write_table(out, temporary, compression='zstd')
    os.chmod(temporary, 0o600)
    check = pq.read_table(temporary)
    if not check.select(original.column_names).equals(original) or check.num_rows != 10000:
        raise RuntimeError('persisted bridge columns/row order not preserved')
    temporary.replace(dest)
    coverage = {'rows': 10000,
                'candidate_match_states': dict(Counter(cstates)),
                'records_match_states': dict(Counter(rstates)),
                'ads_with_cross_source_or_bridge_conflict': sum(bool(x) for x in conflicts),
                'fields': {field: {'available': sum(x is not None for x in added[field]),
                                   'missing': sum(x is None for x in added[field]),
                                   'blank': sum(isinstance(x, str) and not x.strip() for x in added[field]),
                                   'source_counts': dict(sources[field])} for field in FIELDS}}
    (public / 'METADATA_COVERAGE_PUBLIC.json').write_text(json.dumps(coverage, indent=2, sort_keys=True) + '\n')
    schema = [{'name': x.name, 'type': str(x.type), 'nullable': x.nullable} for x in out.schema]
    (public / 'RESEARCH_SCHEMA_PUBLIC.json').write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n')
    report = {'version': VERSION, 'status': 'pass', 'job_id': os.environ['SLURM_JOB_ID'],
              'created_utc': datetime.now(timezone.utc).isoformat(), 'code_sha256': sha(__file__),
              'input_bridge_sha256': bridge_sha, 'input_bridge_receipt_sha256': sha(a.bridge_receipt),
              'records_complete_sha256': records_complete['sha256'],
              'records_complete_marker': records_complete,
              'augmented_research_sha256': sha(dest), 'rows': 10000,
              'original_columns_preserved': True, 'original_keys_preserved': True,
              'lookup_source_footer_provenance': {'candidate': cp, 'records': rp},
              'raw_title_recovery': raw_report,
              'private_output': {'rows': 10000, 'sha256': sha(dest)},
              'public_output_sha256': {p.name: sha(p) for p in public.glob('*.json') if p != receipt_path},
              'checks': {'original_columns_types_values_order_preserved': True,
                         'canonical_membership_preserved': True, 'weights_labels_masks_unchanged': True,
                         'no_description_or_evidence_columns_read': True,
                         'metadata_lookup_only_original_keys': True,
                         'duplicate_matches_unavailable_no_arbitrary_row': True,
                         'raw_records_fallback_used': bool(a.raw_records_dir)},
              'limits': ['Sample metadata only; no full-corpus metadata join.',
                         'Records dates are observation dates, not historical body versions.',
                         'COMPANY_ID is a vendor scrape entity, not a consolidated economic firm.',
                         'Missing or duplicate metadata are unavailable; unknown labels remain unchanged.'],
              'runtime': {'python': platform.python_version(), 'duckdb': duckdb.__version__, 'pyarrow': pa.__version__}}
    receipt_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    con.close()
    print(json.dumps({'status': 'pass', 'rows': 10000, 'coverage': coverage}))


if __name__ == '__main__':
    main()
