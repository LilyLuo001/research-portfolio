"""Build a source/version scope register from already-cached metadata only.

No network, credentials, raw advertisements, model calls or old-ledger writes.
Source file metadata identities are explicitly not advertisement identities.
Run only on the Azure VM; local tests use synthetic fixtures.
"""
import argparse
import collections
import csv
import datetime
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import time

CATALOG_REL = 'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl'
CATALOG_SHA = '4265e2469a8d3d35a769faad9c163823b0df32364f88061db5ecc5e131b1eb1e'
PROVIDER_SHAS = {
    'Job Descriptions': 'e9b80c3b59337202b7ee05380f32de9d0cb8d07cf664e0809609cc366625eee3',
    'Job Records': '05cf0d4d2fa1a02119e796e6ab75c838adb21fbed1bf90cd55df825d625f05bd',
}
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
MAX_METADATA_BYTES = 32 * 1024 * 1024
MAX_METADATA_FILES = 650


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_file(path, pins, cap=MAX_METADATA_BYTES):
    if path.is_symlink() or not path.is_file():
        raise ValueError('input_not_regular_file')
    if path.stat().st_size > cap:
        raise ValueError('metadata_size_cap_exceeded')
    data = path.read_bytes()
    pins[str(path)] = digest(data)
    return data


def safe_path(value):
    """Private source names may be kept, signed query strings may not."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('source_path_not_string')
    if '?' in value or '#' in value:
        raise ValueError('signed_or_fragment_path_not_allowed')
    return value


def source_key(name, size, rows):
    name = Path(safe_path(name)).name
    size, rows = int(size), int(rows)
    if size < 0 or rows < 0:
        raise ValueError('negative_metadata_count')
    return name, size, rows


def locator(item):
    m = item['locator']
    return {k: safe_path(m[k]) if isinstance(m[k], str) else m[k]
            for k in ['cluster', 'path', 'root', 'rel', 'size', 'status'] if k in m}


def loaded_metadata(stage, pins):
    inv = json.loads(read_file(stage / 'VERIFIED_DELIVERY_METADATA_PRIVATE.json', pins))
    if not isinstance(inv, list) or len(inv) > MAX_METADATA_FILES:
        raise ValueError('metadata_inventory_cap_or_type')
    output = []
    total = 0
    seen = set()
    for item in inv:
        d = item['sha256']
        if not SHA_RE.fullmatch(d) or d in seen:
            raise ValueError('metadata_digest_invalid_or_duplicate')
        seen.add(d)
        loc = locator(item)
        if any('batch035' in str(x).lower() for x in loc.values()):
            raise ValueError('protected_locator_in_scope_inventory')
        path = stage / 'metadata_cache' / (d + '.metadata')
        b = read_file(path, pins)
        total += len(b)
        if total > MAX_METADATA_BYTES or digest(b) != d:
            raise ValueError('metadata_total_cap_or_SHA_mismatch')
        name = Path(loc['rel']).name
        try:
            value = json.loads(b)
        except (ValueError, UnicodeError):
            if name == 'job_records_manifest.tsv':
                value = list(csv.DictReader(io.StringIO(b.decode()), delimiter='\t'))
            else:
                value = None
        output.append({'sha256': d, 'name': name, 'locator': loc, 'value': value})
    return output, total


def shape(value, depth=0):
    """Field/type inventory only; no private values in the public receipt."""
    if depth > 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {k: shape(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return {'type': 'list', 'length': len(value), 'first_shape': shape(value[0], depth + 1) if value else None}
    return type(value).__name__


def build_register(metadata, catalog, accounting, expected_provider_shas=None):
    expected_provider_shas = expected_provider_shas or PROVIDER_SHAS
    providers, sources, reports, index_versions, inventories, description_maps = [], {}, [], [], [], []
    shapes = {}
    for item in metadata:
        x, name, d = item['value'], item['name'], item['sha256']
        if name == 'job_records_manifest.tsv':
            for r in x:
                k = source_key(r['file'], r['bytes'], r['footer_rows'])
                s = sources.setdefault(k, {'basename': k[0], 'source_bytes': k[1], 'source_footer_rows': k[2],
                                          'row_unit': 'raw_source_footer_row_not_unique_ad', 'footer_manifest_sha256': [], 'derived_versions': []})
                s['footer_manifest_sha256'].append(d)
        if not isinstance(x, dict):
            continue
        if name == 'dewey-audit-manifest.json':
            ds = x.get('describe', {}).get('dataset_name')
            if ds not in expected_provider_shas:
                continue
            files = []
            for f in x.get('files', []):
                n = safe_path(f['file_name'])
                size = int(f['file_size_bytes'])
                files.append({'file_name': n, 'basename': Path(n).name, 'bytes': size,
                              'manifest_file_identity': canonical_hash([d, n, size]),
                              'identity_unit': 'provider_manifest_entry_not_source_content_hash',
                              'base_binding_status': 'not_yet_proved_at_provider_file_level'})
            if len(files) != x.get('metadata', {}).get('total_files'):
                raise ValueError('provider_manifest_incomplete')
            if sum(f['bytes'] for f in files) != x.get('metadata', {}).get('total_size'):
                raise ValueError('provider_manifest_size_mismatch')
            providers.append({'dataset': ds, 'dataset_version': x['describe'].get('dataset_version_timestamp'),
                              'manifest_sha256': d, 'selection_state': 'selected_pinned_scope' if d == expected_provider_shas[ds] else 'other_version_preserved_not_selected',
                              'source_locator': item['locator'], 'files': files})
            shapes.setdefault(ds, shape(x.get('files', [])[:1]))
        elif name == 'index_manifest.json':
            index_versions.append({'metadata_sha256': d, 'locator': item['locator'],
                                   **{k: x.get(k) for k in ['status', 'rows', 'source_files', 'available_source_files', 'output_footer_rows', 'input_manifest_sha256', 'columns', 'output_bytes']},
                                   'records_dir': safe_path(x.get('records_dir')),
                                   'record_source_file_mapping': safe_path(x.get('record_source_file_mapping')),
                                   'selection_state': 'preserved_derived_version_not_ad_count'})
            shapes.setdefault('index_manifest', shape(x))
        elif isinstance(x.get('source'), dict) and 'output_rows' in x:
            s = x['source']
            k = source_key(s['file'], s['bytes'], s['footer_rows'])
            report = {'metadata_sha256': d, 'locator': item['locator'], 'status': x.get('status'),
                      'source_key': list(k), 'skinny_schema_sha256': s.get('skinny_schema_sha256'),
                      'output_rows': int(x['output_rows']), 'output_bytes': x.get('output_bytes'),
                      'outputs': [{'path': safe_path(v['path']), 'bytes': int(v['bytes']), 'rows': int(v['rows']),
                                   'prefix': safe_path(v.get('prefix'))} for v in x.get('outputs', [])],
                      'output_metadata_fields': sorted(x), 'selection_state': 'preserved_derived_version_not_additive'}
            if report['output_rows'] != k[2]:
                raise ValueError('derived_source_row_nonconservation')
            if report['outputs'] and sum(v['rows'] for v in report['outputs']) != k[2]:
                raise ValueError('derived_partition_row_nonconservation')
            reports.append(report)
            shapes.setdefault('per_source_report', shape(x))
        elif name == 'RECORDS_INVENTORY_PRIVATE.json':
            fs = []
            for f in x['files']:
                # Preserve metadata scalar/list values without copying arbitrary credentials.
                q = {k: f[k] for k in ['rows', 'bytes', 'size', 'size_bytes', 'sha256', 'schema_sha256', 'columns', 'source_rows', 'row_groups'] if k in f}
                for k in ['file', 'path', 'relative_path', 'rel', 'blob', 'container', 'source_file', 'source_path', 'source_id']:
                    if isinstance(f.get(k), str):
                        q[k] = safe_path(f[k])
                q['unhandled_field_names'] = sorted(set(f) - set(q))
                fs.append(q)
            inventories.append({'metadata_sha256': d, 'locator': item['locator'], 'kind': x.get('kind'), 'bytes': x.get('bytes'),
                                'complete_sha256': x.get('complete_sha256'), 'inventory_sha256': x.get('inventory_sha256'),
                                'files': fs, 'selection_state': 'existing_execution_inventory_candidate_not_new_source',
                                'source_binding_status': 'requires_explicit_per_file_source_locator'})
            shapes.setdefault('records_inventory', shape(x))
        elif name == 'description_regions_disjoint_manifest.json':
            allocations = []
            for cluster in ['kunshan', 'wuzhen']:
                for f in x.get(cluster, []):
                    if not SHA_RE.fullmatch(str(f.get('sha256', ''))):
                        raise ValueError('allocation_source_SHA_invalid')
                    allocations.append({'cluster': cluster, 'file_name': safe_path(f['file_name']),
                                        'basename': Path(safe_path(f['file_name'])).name,
                                        'original_path': safe_path(f['path']), 'bytes': int(f['bytes']),
                                        'source_sha256_from_existing_manifest': f['sha256']})
            if len(allocations) != x.get('union_count') or sum(a['bytes'] for a in allocations) != x.get('union_bytes'):
                raise ValueError('description_allocation_count_size_mismatch')
            description_maps.append({'metadata_sha256': d, 'locator': item['locator'], 'shape': shape(x),
                                     'reported_union_count': x.get('union_count'), 'reported_union_bytes': x.get('union_bytes'),
                                     'allocations': allocations,
                                     'binding_status': 'provider_file_to_recorded_source_SHA_and_allocation_map_not_source_to_ad_identity'})
            shapes.setdefault('description_allocation', shape(x))

    selected = [p for p in providers if p['selection_state'] == 'selected_pinned_scope']
    if collections.Counter(p['dataset'] for p in selected) != collections.Counter(expected_provider_shas.keys()):
        raise ValueError('pinned_provider_missing_or_duplicate')
    source_report_only = []
    for r in reports:
        k = tuple(r['source_key'])
        if k not in sources:
            source_report_only.append(r)
        else:
            sources[k]['derived_versions'].append(r)
    record_provider = next(p for p in selected if p['dataset'] == 'Job Records')
    provider_lookup = collections.defaultdict(list)
    for f in record_provider['files']:
        provider_lookup[(f['basename'], f['bytes'])].append(f['manifest_file_identity'])
    allocation_lookup = collections.defaultdict(list)
    for v in description_maps:
        for a in v['allocations']:
            allocation_lookup[(a['basename'], a['bytes'])].append((v['metadata_sha256'], a))
    description_provider = next(p for p in selected if p['dataset'] == 'Job Descriptions')
    for f in description_provider['files']:
        matches = allocation_lookup.get((f['basename'], f['bytes']), [])
        hashes = {a['source_sha256_from_existing_manifest'] for _, a in matches}
        f['raw_source_sha256_from_existing_allocation'] = next(iter(hashes)) if len(hashes) == 1 else None
        f['allocation_metadata_sha256'] = sorted({d for d, _ in matches})
        f['source_content_hash_binding'] = ('unique_provider_name_size_to_existing_verified_source_SHA' if len(hashes) == 1 else
                                            'no_unique_existing_allocation_SHA_binding')
    for k, s in sources.items():
        matches = provider_lookup.get(k[:2], [])
        s['provider_manifest_entries'] = matches
        s['provider_binding'] = 'unique_basename_size_metadata_match' if len(matches) == 1 else 'missing_or_ambiguous_metadata_match'
        s['selected_once_as_raw_source_metadata'] = len(matches) == 1
        s['raw_source_sha256'] = None
        s['source_hash_status'] = 'not_attested_by_footer_manifest_no_hash_invented'
        s['identity_columns_declared_by_complete_index_manifests'] = sorted({c for v in index_versions if v['status'] == 'complete' for c in (v['columns'] or [])})
        s['row_identity_is_source_file_plus_RECORD_SOURCE_ROW'] = 'RECORD_SOURCE_ROW' in s['identity_columns_declared_by_complete_index_manifests']
        s['advertisement_identity_bridge_status'] = 'not_row_joined'
        s['derived_schema_versions'] = sorted({v['skinny_schema_sha256'] for v in s['derived_versions'] if v['skinny_schema_sha256']})
    output_lookup = collections.defaultdict(list)
    for r in reports:
        for part in r['outputs']:
            output_lookup[(Path(part['path']).name, part['bytes'], part['rows'])].append(r)
    inventory_statuses = collections.Counter()
    for inventory in inventories:
        for part in inventory['files']:
            p = next((part[k] for k in ['path', 'file', 'relative_path', 'rel', 'blob'] if isinstance(part.get(k), str)), None)
            size = part.get('bytes', part.get('size', part.get('size_bytes')))
            matches = output_lookup.get((Path(p).name, size, part.get('rows')), []) if p else []
            keys = {tuple(m['source_key']) for m in matches}
            part['source_metadata_keys'] = [list(k) for k in sorted(keys)]
            part['source_report_metadata_sha256'] = sorted({m['metadata_sha256'] for m in matches})
            part['source_binding_status'] = ('unique_basename_size_rows_source_metadata_match' if len(keys) == 1 else
                                             'ambiguous_source_metadata_match' if keys else 'no_preserved_source_metadata_match')
            part['mapping_does_not_attest_output_content_SHA'] = True
            inventory_statuses[part['source_binding_status']] += 1
        inventory['source_binding_status'] = 'per_file_metadata_matches_recorded_not_row_identity_join'
        inventory['complete_index_manifest_SHA_matches'] = [v['metadata_sha256'] for v in index_versions
                                                           if v['status'] == 'complete' and v['metadata_sha256'] == inventory.get('complete_sha256')]
    # The existing combined accounting has shard IDs, not provider file names.
    ac = {a['shard_id']: a for a in accounting}
    if len(ac) != len(accounting):
        raise ValueError('duplicate_accounting_shards')
    base = []
    for r in catalog:
        a = ac.get(r['shard_id'])
        if not a or a['canonical_US_ads'] != r['ad_rows'] or a['catalog_receipt_sha256'] != r['original_receipt_sha256']:
            raise ValueError('base_catalog_combined_accounting_mismatch')
        base.append({'shard_id': r['shard_id'], 'ad_rows': r['ad_rows'], 'ad_bytes': r['ad_bytes'],
                     'ad_path': safe_path(r['ad_path']), 'ad_sha256': r['ad_sha256_from_original_receipt'],
                     'catalog_receipt_sha256': r['original_receipt_sha256'], 'raw_rows': a['raw_rows'],
                     'source_bytes': a['source_bytes'], 'country_scope': 'US_canonical_existing_base',
                     'selection_state': 'reuse_existing_base_once', 'provider_file_binding': 'not_available_in_combined_accounting',
                     'raw_to_canonical_mapping_not_reconstructed': True})
    if len({b['shard_id'] for b in base}) != len(base) or set(ac) != {b['shard_id'] for b in base}:
        raise ValueError('base_shard_identity_set_mismatch')
    counts = {
        'provider_files': {p['dataset']: len(p['files']) for p in selected},
        'provider_bytes': {p['dataset']: sum(f['bytes'] for f in p['files']) for p in selected},
        'Records_source_metadata_keys': len(sources),
        'Records_source_footer_rows_once': sum(s['source_footer_rows'] for s in sources.values()),
        'Records_source_bytes_once': sum(s['source_bytes'] for s in sources.values()),
        'Records_sources_with_unique_provider_name_size_binding': sum(s['provider_binding'] == 'unique_basename_size_metadata_match' for s in sources.values()),
        'Records_sources_with_derived_report': sum(bool(s['derived_versions']) for s in sources.values()),
        'Records_source_reports_preserved': len(reports),
        'Records_source_reports_without_footer_source_binding': len(source_report_only),
        'Records_derived_schema_version_count_distribution': dict(collections.Counter(len(s['derived_schema_versions']) for s in sources.values())),
        'Records_index_manifest_versions': len(index_versions),
        'Records_inventory_files': sum(len(v['files']) for v in inventories),
        'Records_inventory_rows_not_additive': sum(int(f.get('rows', 0)) for v in inventories for f in v['files']),
        'Records_inventory_source_binding_statuses': dict(inventory_statuses),
        'base_shards': len(base), 'base_canonical_US_ads_from_receipts': sum(b['ad_rows'] for b in base),
        'description_raw_rows_from_combined_accounting': sum(b['raw_rows'] for b in base),
        'description_source_bytes_from_combined_accounting': sum(b['source_bytes'] for b in base),
        'Description_provider_files_with_existing_source_SHA_binding': sum(f['raw_source_sha256_from_existing_allocation'] is not None for f in description_provider['files']),
        'exact_provider_Description_file_to_base_shard_bindings': 0,
        'global_unique_ads': None, 'global_unique_normalized_contexts': None, 'global_per_field_missing_inputs': None,
    }
    if counts['description_source_bytes_from_combined_accounting'] != counts['provider_bytes']['Job Descriptions']:
        raise ValueError('description_provider_aggregate_size_mismatch')
    if counts['Records_source_bytes_once'] != counts['provider_bytes']['Job Records'] or counts['Records_source_metadata_keys'] != counts['provider_files']['Job Records']:
        raise ValueError('Records_provider_footer_scope_mismatch')
    if source_report_only or counts['Records_sources_with_unique_provider_name_size_binding'] != len(sources):
        raise ValueError('Records_source_binding_incomplete')
    return {'providers': providers, 'records_sources': list(sources.values()), 'source_report_only': source_report_only,
            'index_versions': index_versions, 'records_inventories': inventories, 'description_maps': description_maps,
            'base_shards': base, 'counts': counts, 'shapes': shapes}


def write_json(path, value):
    if path.exists():
        raise ValueError('existing_output_preserved')
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
    return {'file': path.name, 'bytes': len(data), 'sha256': digest(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(Path.home() / 'migration'))
    parser.add_argument('--output', default='scope_continuation_20261117/run001')
    args = parser.parse_args()
    root = Path(args.root).resolve(); out = root / args.output
    if out.resolve().is_relative_to(root) is False:
        raise ValueError('output_outside_migration')
    os.umask(0o077); out.mkdir(parents=True, exist_ok=True)
    lock = (out / 'SCOPE_REGISTER.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    done = out / 'SCOPE_REGISTER_PUBLIC.json'
    if done.exists():
        saved = json.loads(done.read_text())
        for p in saved['outputs']:
            if digest((out / p['file']).read_bytes()) != p['sha256']:
                raise ValueError('completed_output_changed')
        for path, d in json.loads((out / 'INPUT_PINS_PRIVATE.json').read_text()).items():
            if digest(Path(path).read_bytes()) != d:
                raise ValueError('completed_register_input_changed')
        print(json.dumps({'status': 'existing_register_verified_no_reexecution', 'receipt_sha256': digest(done.read_bytes())}))
        return
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    signal.alarm(300)
    t0 = time.monotonic(); pins = {}; stage = root / 'execution_20261116/run001/stage1'
    metadata, metadata_bytes = loaded_metadata(stage, pins)
    cb = read_file(root / CATALOG_REL, pins)
    if digest(cb) != CATALOG_SHA:
        raise ValueError('catalog_pin_mismatch')
    catalog = [json.loads(l) for l in cb.splitlines() if l]
    accounting = json.loads(read_file(stage / 'ALL_SHARD_ACCOUNTING_PRIVATE.json', pins))
    result = build_register(metadata, catalog, accounting)
    if result['counts']['base_shards'] != 2464 or result['counts']['Records_source_metadata_keys'] != 269:
        raise ValueError('frozen_source_count_mismatch')
    if result['counts']['base_canonical_US_ads_from_receipts'] != 204774035 or result['counts']['Records_source_footer_rows_once'] != 356449214:
        raise ValueError('frozen_count_mismatch')
    outputs = []
    for name, key in [('PROVIDER_SCOPE_REGISTER_PRIVATE.json', 'providers'),
                      ('RECORDS_SOURCE_VERSION_REGISTER_PRIVATE.json', 'records_sources'),
                      ('RECORDS_INDEX_VERSIONS_PRIVATE.json', 'index_versions'),
                      ('RECORDS_EXECUTION_INVENTORIES_PRIVATE.json', 'records_inventories'),
                      ('DESCRIPTION_ALLOCATION_METADATA_PRIVATE.json', 'description_maps'),
                      ('BASE_SHARD_SCOPE_REGISTER_PRIVATE.json', 'base_shards')]:
        outputs.append(write_json(out / name, result[key]))
    for p, d in pins.items():
        if digest(Path(p).read_bytes()) != d:
            raise ValueError('input_changed_during_read')
    outputs.append(write_json(out / 'INPUT_PINS_PRIVATE.json', pins))
    report = {'at_utc': utcnow(), 'status': 'source_version_metadata_register_complete_row_identity_bridge_pending',
              'scope': 'already verified two provider manifests and existing base/Records metadata, not all future deliveries',
              'counts': result['counts'], 'metadata_files_read': len(metadata), 'metadata_bytes_read': metadata_bytes,
              'source_schema_shapes_only': result['shapes'], 'outputs': outputs,
              'row_unit_warning': 'Description rows, Records rows, US base ads and derivative index rows are not additive.',
              'completion_limits': ['No source row or advertisement key union/join executed.',
                                    'Provider name/size metadata matching is not a content-SHA or ad-identity match.',
                                    'Description source hashes are reused from a pinned existing allocation manifest; raw files were not rehashed.',
                                    'No full normalized-context hash index established.',
                                    'Fine semantic states and existing value reuse are preserved, not recomputed.'],
              'next_dependency': 'Inspect an existing complete Records output inventory and base-ad schema; choose a provenance-pinned narrow-column join only after explicit source-row linkage exists.',
              'inputs_unchanged': True, 'raw_advertisement_files_read': 0, 'individual_receipt_rescans': 0,
              'network_calls': 0, 'model_calls': 0, 'old_ledger_writes': 0, 'new_resources': 0,
              'elapsed_seconds': time.monotonic() - t0, 'max_wall_seconds': 300, 'max_address_space_bytes': 1024 ** 3,
              'code_sha256': digest(Path(__file__).read_bytes()),
              'infrastructure_cap_not_reset': True, 'new_model_queue_released': False}
    write_json(done, report)
    signal.alarm(0)
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'receipt_sha256': digest(done.read_bytes()),
                      'elapsed_seconds': report['elapsed_seconds'], 'network_calls': 0, 'model_calls': 0}))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # No raw exception message/traceback may leak metadata locators or values.
        code = str(e) if isinstance(e, ValueError) and re.fullmatch(r'[A-Za-z0-9_]{1,100}', str(e)) else None
        print(json.dumps({'status': 'metadata_register_failed_preserve_inputs_and_outputs', 'error_type': type(e).__name__, 'safe_error_code': code}))
        raise SystemExit(2)
