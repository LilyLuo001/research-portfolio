"""Derive missing provider-to-base provenance from cached publication receipts.

Azure execution only. This is not ad matching, accounting recomputation, content
rehashing, extraction, or semantic acceptance. Local tests are synthetic.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import time

SHA_RE = re.compile(r'^[0-9a-f]{64}$')
SCOPE_SHA = '706960401b9d1783093cef26e28751de39355c0812c9b71a85e6950a9f48dd9b'
MAX_FILES = 2464
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_PIN_METADATA_BYTES = 32 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def valid_sha(value):
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError('invalid_source_sha')
    return value


def basename(value):
    if not isinstance(value, str) or not value or any(x in value for x in ('?', '#', '\\', '\x00')):
        raise ValueError('invalid_source_path')
    return PurePosixPath(value).name


def integer(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('invalid_source_size')
    return value


def read_verified(path, expected, cap):
    valid_sha(expected)
    if path.is_symlink() or not path.is_file():
        raise ValueError('pinned_input_missing_or_not_regular')
    n = path.stat().st_size
    if n > cap:
        raise ValueError('pinned_input_size_cap')
    with path.open('rb') as f:
        data = f.read(cap + 1)
    if len(data) != n or sha(data) != expected:
        raise ValueError('pinned_input_SHA_mismatch')
    return json.loads(data), len(data)


def build_lookups(providers, allocations):
    selected = [p for p in providers if p.get('dataset') == 'Job Descriptions' and
                p.get('selection_state') == 'selected_pinned_scope']
    if len(selected) != 1:
        raise ValueError('selected_Description_provider_not_unique')
    p = selected[0]
    provider = collections.defaultdict(list)
    for f in p['files']:
        h = valid_sha(f['raw_source_sha256_from_existing_allocation'])
        n = integer(f['bytes']); name = basename(f['file_name'])
        provider[(h, n, name)].append({'provider_manifest_sha256': p['manifest_sha256'],
              'provider_manifest_entry_identity': f['manifest_file_identity'],
              'provider_file_name': f['file_name']})
    allocation = collections.defaultdict(list)
    for manifest in allocations:
        for f in manifest['allocations']:
            h = valid_sha(f['source_sha256_from_existing_manifest'])
            n = integer(f['bytes']); name = basename(f['file_name'])
            if basename(f['original_path']) != name:
                raise ValueError('allocation_original_path_basename_disagrees')
            entry = {'allocation_metadata_sha256': manifest['metadata_sha256'],
                     'allocation_source_path': f['original_path'], 'allocation_cluster': f['cluster']}
            if entry not in allocation[(h, n, name)]:
                allocation[(h, n, name)].append(entry)
    return provider, allocation


def bind_one(row, base, receipt, provider, allocation):
    """Only declared source provenance fields are used; no row/evidence payload."""
    result = {'shard_id': row['shard_id'],
              'publication_receipt_sha256': row['publication_receipt_sha256'],
              'base_artifact_sha256_from_existing_register': base['ad_sha256'],
              'status': 'unresolved_source_binding'}
    if receipt.get('shard_id') != row['shard_id']:
        result['reason'] = 'publication_shard_identity_mismatch'; return result
    complete = receipt.get('shard_complete')
    if not isinstance(complete, dict):
        result['reason'] = 'missing_shard_complete'; return result
    a, lean = complete.get('accounting'), complete.get('lean_complete')
    if not isinstance(a, dict) or not isinstance(lean, dict):
        result['reason'] = 'missing_source_metadata_sections'; return result
    try:
        ah, lh = valid_sha(a['source_sha256_cached']), valid_sha(lean['source_sha256'])
        an, ln = integer(a['source_bytes']), integer(lean['source_bytes'])
        ap, lp = a['source_file'], lean['source']
        ab, lb = basename(ap), basename(lp)
    except (KeyError, ValueError, TypeError):
        result['reason'] = 'source_fields_missing_or_invalid'; return result
    if a.get('shard_id') != row['shard_id']:
        result['reason'] = 'accounting_shard_identity_mismatch'; return result
    if ah != lh or an != ln or an != row['source_bytes'] or ab != lb:
        result['reason'] = 'cached_source_sections_disagree'; return result
    key = (ah, an, ab)
    ps = provider.get(key, []); alloc = allocation.get(key, [])
    identities = {p['provider_manifest_entry_identity'] for p in ps}
    if len(identities) != 1:
        result['reason'] = 'provider_identity_ambiguous' if identities else 'no_provider_source_SHA_size_name_match'
        return result
    if not alloc:
        result['reason'] = 'no_allocation_source_SHA_size_name_match'; return result
    allocation_paths = {f['allocation_source_path'] for f in alloc}
    exact_path = ap == lp and ap in allocation_paths
    # Source hashes/size are equal and all path basenames agree. Different
    # root paths are retained as relocations; never reported as exact full path.
    result.update(status='source_provenance_bound', source_sha256_from_cached_receipts=ah,
       source_bytes=an, source_basename=ab, accounting_source_path=ap, lean_source_path=lp,
       path_binding='identical_full_path' if exact_path else 'identical_basename_SHA_size_distinct_roots_preserved',
       source_hash_recomputed_in_this_run=False, provider=ps[0], allocation_sources=alloc,
       advertisement_row_identity_join_executed=False)
    return result


def write_json(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
    return {'file': path.name, 'bytes': len(data), 'sha256': sha(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(Path.home() / 'migration'))
    parser.add_argument('--output', default='source_binding_20261118/run001')
    parser.add_argument('--max-receipt-mib', type=int, default=384)
    args = parser.parse_args()
    if not 1 <= args.max_receipt_mib <= 384:
        raise ValueError('receipt_cap_outside_explicit_window')
    root = Path(args.root).resolve(); out = root / args.output
    if not out.resolve().is_relative_to(root) or out == root:
        raise ValueError('output_outside_migration')
    os.umask(0o077)
    # Never overwrite or resume a prior run implicitly.
    out.mkdir(parents=True, exist_ok=True)
    with (out/'SOURCE_BINDING_STARTED_PUBLIC.json').open('x') as guard:
        json.dump({'at_utc':utc(),'status':'exclusive_source_binding_started','model_calls':0},guard)
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    signal.alarm(120); started = time.monotonic()
    scope = root / 'scope_continuation_20261117/run001'
    stage = root / 'execution_20261116/run001/stage1'
    public, n = read_verified(scope/'SCOPE_REGISTER_PUBLIC.json', SCOPE_SHA, 1024*1024)
    outputs = {p['file']: p['sha256'] for p in public['outputs']}
    pins = {}; meta_bytes = n
    for name in ['PROVIDER_SCOPE_REGISTER_PRIVATE.json', 'DESCRIPTION_ALLOCATION_METADATA_PRIVATE.json',
                 'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json', 'INPUT_PINS_PRIVATE.json']:
        value, n = read_verified(scope/name, outputs[name], MAX_PIN_METADATA_BYTES)
        pins[name] = value; meta_bytes += n
    if meta_bytes > MAX_PIN_METADATA_BYTES:
        raise ValueError('register_metadata_total_cap')
    old_input_pins = pins['INPUT_PINS_PRIVATE.json']
    accounting_path = stage/'ALL_SHARD_ACCOUNTING_PRIVATE.json'
    accounting_sha = old_input_pins.get(str(accounting_path))
    if not accounting_sha:
        raise ValueError('accounting_input_pin_missing')
    accounting, n = read_verified(accounting_path, accounting_sha, MAX_PIN_METADATA_BYTES)
    meta_bytes += n
    if meta_bytes > MAX_PIN_METADATA_BYTES or len(accounting) != MAX_FILES:
        raise ValueError('accounting_scope_or_metadata_cap')
    bases = {b['shard_id']: b for b in pins['BASE_SHARD_SCOPE_REGISTER_PRIVATE.json']}
    if len(bases) != MAX_FILES or len({r['shard_id'] for r in accounting}) != MAX_FILES or set(bases) != {r['shard_id'] for r in accounting}:
        raise ValueError('base_accounting_identity_set_disagrees')
    provider, allocation = build_lookups(pins['PROVIDER_SCOPE_REGISTER_PRIVATE.json'],
                                        pins['DESCRIPTION_ALLOCATION_METADATA_PRIVATE.json'])
    rows = sorted(accounting, key=lambda r: r['shard_id'])
    max_bytes = args.max_receipt_mib * 1024 * 1024
    read_bytes = 0; processed = 0; status_counts = collections.Counter(); reasons = collections.Counter()
    path_counts = collections.Counter(); source_shas = set(); provider_ids = set(); provider_multiplicity = collections.Counter()
    bindings = []; receipt_pins = {}; halt = None
    for row in rows:
        if time.monotonic() - started > 112:
            halt = 'time_cap_preserved_partial_mapping'; break
        h = valid_sha(row['publication_receipt_sha256']); path = stage/'metadata_cache'/(h+'.metadata')
        if not path.is_file() or path.is_symlink():
            halt = 'cached_receipt_missing_or_not_regular'; break
        if read_bytes + path.stat().st_size > max_bytes:
            halt = 'metadata_byte_cap_preserved_partial_mapping'; break
        receipt, n = read_verified(path, h, MAX_RECEIPT_BYTES)
        read_bytes += n; receipt_pins[h] = n
        base = bases[row['shard_id']]
        if row['catalog_receipt_sha256'] != base['catalog_receipt_sha256']:
            raise ValueError('base_analysis_receipt_pin_disagrees')
        result = bind_one(row, base, receipt, provider, allocation)
        bindings.append(result); processed += 1; status_counts[result['status']] += 1
        if result['status'] == 'source_provenance_bound':
            path_counts[result['path_binding']] += 1
            source_shas.add(result['source_sha256_from_cached_receipts'])
            provider_ids.add(result['provider']['provider_manifest_entry_identity'])
            provider_multiplicity[result['provider']['provider_manifest_entry_identity']] += 1
        else:
            reasons[result['reason']] += 1
    content = b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n').encode() for r in bindings)
    if len(content) > MAX_OUTPUT_BYTES:
        raise ValueError('private_output_cap')
    crosswalk = out/'DESCRIPTION_TO_BASE_SOURCE_BINDING_PRIVATE.jsonl'
    with crosswalk.open('xb') as f: f.write(content)
    private_inputs = {'scope_register_sha256': SCOPE_SHA, 'accounting_sha256': accounting_sha,
                      'registered_output_pins': outputs, 'publication_receipts_SHA_verified': receipt_pins}
    manifests = [write_json(out/'SOURCE_BINDING_INPUT_PINS_PRIVATE.json', private_inputs)]
    manifests.append({'file': crosswalk.name, 'bytes': len(content), 'sha256': sha(content)})
    # Input bytes were SHA-verified on read. No input is opened for writing.
    report = {'at_utc': utc(), 'status': halt or ('source_mapping_complete' if not reasons else 'source_mapping_examined_with_unresolved'),
       'source_mapping_scope':'selected_existing_Description_provider_files_to_existing_US_base_shards',
       'target_base_shards': MAX_FILES, 'processed_cached_publication_receipts': processed,
       'remaining_cached_publication_receipts': MAX_FILES-processed, 'mapping_status_counts':dict(status_counts),
       'unresolved_reason_counts':dict(reasons), 'path_binding_counts':dict(path_counts),
       'distinct_source_SHA_bound':len(source_shas), 'distinct_provider_entries_bound':len(provider_ids),
       'provider_entries_with_multiple_base_bindings':sum(n>1 for n in provider_multiplicity.values()),
       'all_provider_entries_bound_once':len(provider_ids)==MAX_FILES and all(n==1 for n in provider_multiplicity.values()),
       'publication_receipt_bytes_read': read_bytes, 'register_metadata_bytes_read':meta_bytes,
       'max_publication_receipt_bytes':max_bytes, 'max_receipts':MAX_FILES,
       'max_single_receipt_bytes':MAX_RECEIPT_BYTES,
       'cap_basis_prior_publication_receipt_bytes':317184716,
       'cap_authorization':'root_explicit_384MiB_cached_metadata_window_not_financial_budget_reset',
       'elapsed_seconds':time.monotonic()-started, 'wall_limit_seconds':120, 'memory_limit_bytes':1024**3,
       'outputs':manifests, 'code_sha256':sha(Path(__file__).read_bytes()),
       'source_inputs_opened_for_writing':0, 'previous_registers_overwritten':0,
       'source_body_files_read':0,'source_body_content_SHA_recomputed':False,
       'network_calls':0,'model_calls':0,'new_resources':0,'new_semantically_accepted':0,
       'new_advertisement_identity_joins':0,'global_unique_ads':None,'global_per_field_missing_inputs':None,
       'stage1_stage2_and_phase_budgets_reset':False,
       'interpretation':'Existing cached receipt declarations now bind provider source files to base shards. Not a new source-body hash check, advertisement-level join or semantic acceptance.'}
    write_json(out/'DESCRIPTION_TO_BASE_SOURCE_BINDING_PUBLIC.json',report)
    signal.alarm(0)
    print(json.dumps({'status':report['status'], 'processed':processed,'remaining':MAX_FILES-processed,
                      'mapping_status_counts':dict(status_counts),'distinct_provider_entries_bound':len(provider_ids),
                      'publication_receipt_bytes_read':read_bytes,'elapsed_seconds':report['elapsed_seconds'],
                      'receipt_sha256':sha((out/'DESCRIPTION_TO_BASE_SOURCE_BINDING_PUBLIC.json').read_bytes()),
                      'model_calls':0,'network_calls':0}))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        safe = str(e) if isinstance(e, ValueError) and re.fullmatch(r'[a-zA-Z0-9_]{1,100}',str(e)) else None
        print(json.dumps({'status':'source_binding_stopped_preserve_outputs','error_type':type(e).__name__,'safe_error_code':safe}))
        raise SystemExit(2)
