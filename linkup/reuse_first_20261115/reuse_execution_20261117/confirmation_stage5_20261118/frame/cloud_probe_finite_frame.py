"""Azure metadata-only cursor/finite-window probe; no network or text reads.

Run through the existing VM Agent as linkup. New artifacts remain on Azure.
The resulting <=150 canonical-row window is NOT yet a certified fresh-context
frame: base files have no context SHA. A subsequent bounded normalization pass
must filter its hashes against the saved union before any model exposure.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

R = Path.home() / 'migration'
O = R / 'confirmation_stage5_20261118/frame_probe_v1'
B = R / 'integration_20261116/run001'
E = R / 'execution_20261116/run001'
SHA = re.compile(r'^[0-9a-f]{64}$')
CAT_SHA = '4265e2469a8d3d35a769faad9c163823b0df32364f88061db5ecc5e131b1eb1e'
MAP_SHA = '70dadccd266bb70131c40d2573a6d8f81af1978951a7331137fadc134c45f11a'
SCOPE_SHA = '706960401b9d1783093cef26e28751de39355c0812c9b71a85e6950a9f48dd9b'
PROTECTED = '01a17beb-973b-74e2-adbb-20f8d004b1fc'
pins, totals, excluded, reasons = {}, collections.Counter(), set(), []


def read(p, expected=None, lines=False):
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 32 * 1024**2:
        raise ValueError('metadata_file_missing_symlink_or_size_cap')
    data = p.read_bytes(); h = hashlib.sha256(data).hexdigest()
    if expected and h != expected:
        raise ValueError('metadata_SHA_mismatch')
    totals['metadata_bytes_read'] += len(data)
    if totals['metadata_bytes_read'] > 192 * 1024**2:
        raise ValueError('metadata_total_cap')
    pins[str(p.relative_to(R))] = h
    return [json.loads(x) for x in data.splitlines() if x.strip()] if lines else json.loads(data)


def contexts(x):
    """Metadata only; artifact SHA fields are deliberately not context IDs."""
    found = set()
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(k, str) and SHA.fullmatch(k):
                found.add(k)  # Conservative for context-keyed current ledgers.
            if k in ('context_sha256', 'normalized_context_sha256', 'h'):
                vs = v if isinstance(v, list) else [v]
                found.update(y for y in vs if isinstance(y, str) and SHA.fullmatch(y))
            if k == 'record_id' and isinstance(v, str) and v.startswith('corpus-pro-') and SHA.fullmatch(v[11:]):
                found.add(v[11:])
            found.update(contexts(v))
    elif isinstance(x, list):
        for v in x: found.update(contexts(v))
    return found


def ro(p):
    if not p.is_file() or p.is_symlink(): raise ValueError('metadata_database_missing')
    c = sqlite3.connect(p.as_uri() + '?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    return c


def save(name, x):
    b = (json.dumps(x, indent=2, sort_keys=True) + '\n').encode()
    with (O / name).open('xb') as f: f.write(b)
    return hashlib.sha256(b).hexdigest()


def main():
    os.umask(0o077)
    O.mkdir(parents=True, exist_ok=False)
    idxp = B / 'revision003/STATUS_INDEX_PRIVATE.sqlite'
    idx = ro(idxp)
    state_counts = dict(idx.execute('select state,count(*) from final_status group by state'))
    excluded.update(h for h, in idx.execute('select h from final_status'))
    excluded.update(h for h, in idx.execute('select h from blocked'))
    idx.close()
    totals['all_status_contexts_excluded'] = len(excluded)
    # All final statuses, including identity-only/not_reconciled, stay excluded.
    discovery = read(B / 'DISCOVERY_PRIVATE.json')['metadata_inventory']
    manifest_rows, preps, cached = {}, {}, set()
    skipped_protected = 0
    for m in discovery:
        rel, path, h = m['rel'], m['path'], m['sha256']
        if not (rel.endswith('PACKET_MANIFEST_PRIVATE.jsonl') or rel.endswith('PACKET_PREPARATION_PUBLIC.json')):
            continue
        if 'batch035' in path.lower() or PROTECTED in path:
            skipped_protected += 1; continue
        match = re.search(r'batch(\d+)', path)
        if not match: continue
        p = B / 'metadata_cache' / (h + '.metadata')
        if not p.is_file():
            reasons.append('cataloged_preparation_metadata_not_cached'); continue
        is_manifest = rel.endswith('PACKET_MANIFEST_PRIVATE.jsonl')
        x = read(p, h, is_manifest); cached.add(h)
        if is_manifest:
            if any('full_document' in row for row in x): raise ValueError('unexpected_text_in_manifest')
            manifest_rows[h] = x; excluded.update(contexts(x))
        else:
            mh = x.get('packet_manifest_sha256') or x.get('output_sha256', {}).get('packet_manifest_private')
            if mh: preps[(int(match.group(1)), h)] = {'manifest_sha256': mh, 'receipt': x, 'path': path}
    # Exact known metadata files; never inputs, result payloads, raw files, or history.
    metadata = [R/'AZURE_RESEARCH_IDENTITIES_PRIVATE.json',
        R/'astra/extraction/STATE_PRIVATE.json',
        R/'reuse_first_20261115/run01/benchmark20/SELECTION_PRIVATE.json',
        E/'qualification_frame_v1/FRAME_PRIVATE.json']
    for d in [R/'opencode_kimi_20261115/run01', R/'opencode_kimi_20261115/run01/bulk_1309_20261115',
              E/'qualification500_v1', E/'continuation01', E/'continuation02']:
        for name in ['CANDIDATE_STATE_PRIVATE.json', 'CLAIM_PRIVATE.json', 'STATE_PRIVATE.json',
                     'QUARANTINE_EVENTS_PRIVATE.json', 'EXCLUSIONS_PRIVATE.json',
                     'RUNTIME_EXCLUSIONS_PRIVATE.json', 'ACCOUNTING_PENDING_PRIVATE.json',
                     'ACCOUNTING_COMMITTED_PRIVATE.json']:
            p = d/name
            if p.is_file(): metadata.append(p)
    for p in metadata:
        if p.is_file():
            excluded.update(contexts(read(p))); totals['exposure_metadata_files_read'] += 1
        else: reasons.append('required_exposure_metadata_missing:' + p.name)
    for p in [E/'stage2/REUSED_VALUES_PRIVATE.sqlite', E/'stage2/revision002/REUSED_VALUES_PRIVATE.sqlite']:
        if p.is_file():
            c = ro(p)
            names = {n for n, in c.execute("select name from sqlite_master where type='table'")}
            for table in ['document', 'protected']:
                if table in names: excluded.update(h for h, in c.execute('select distinct h from '+table))
            c.close()
    # Inventory current preparation receipts and manifests using existing ledgers.
    # No protected file is opened and no Blob/network fetch is performed.
    ledger_meta, ledger_handles = [], []
    for cluster in ['kunshan', 'wuzhen', 'huazhong']:
        c = ro(R/cluster/'LEDGER_PRIVATE.sqlite'); ledger_handles.append((cluster, c))
        for path, root, rel, size, status, h in c.execute("select path,root,rel,size,status,sha from files where path like '%corpus_pro_review_20261026%' and (rel like '%PACKET_PREPARATION_PUBLIC.json' or rel like '%PACKET_MANIFEST_PRIVATE.jsonl')"):
            if status != 'verified' or 'batch035' in path.lower() or PROTECTED in path: continue
            mt = re.search(r'batch(\d+)', path)
            if mt:
                ledger_meta.append(dict(cluster=cluster, path=path, root=root, rel=rel, size=size, sha256=h, batch=int(mt.group(1))))
    newest_batch = max((m['batch'] for m in ledger_meta), default=0)
    missing_metadata = [m for m in ledger_meta if m['sha256'] not in cached]
    # Missing old duplicate receipts do not invent a newer cursor; any later
    # manifest/preparation, however, prevents admitting this window.
    valid = [(k, v) for k, v in preps.items() if v['manifest_sha256'] in manifest_rows]
    if not valid: raise ValueError('no_cached_SHA_bound_preparation_and_manifest')
    (batch, receipt_sha), last = max(valid, key=lambda kv: kv[0][0])
    newest_variants = {(v['manifest_sha256'], json.dumps(v['receipt'].get('next_cursor'), sort_keys=True))
                       for k, v in valid if k[0] == batch}
    if len(newest_variants) != 1: raise ValueError('latest_preparation_metadata_conflicts')
    receipt = last['receipt']; mh = last['manifest_sha256']
    if receipt.get('status') != 'prepared_not_reviewed' or len(manifest_rows[mh]) != receipt['prepared_contexts']:
        raise ValueError('latest_preparation_count_or_status_disagrees')
    if newest_batch > batch: reasons.append('newer_preparation_metadata_must_be_cached_first')
    cursor = receipt['next_cursor']; ordinal, start = cursor['shard_ordinal'], cursor['row_offset']
    catalog = read(R/'full_scope_catalog_preflight_20261115/20261115T120402Z/CORPUS_RELEASE_CATALOG_PRIVATE.jsonl', CAT_SHA, True)
    if len(catalog) != 2464 or not 0 <= ordinal < 2464: raise ValueError('catalog_or_cursor_scope')
    row = catalog[ordinal]
    if not 0 <= start < row['ad_rows']: raise ValueError('cursor_row_outside_catalog_shard')
    scope = R/'scope_continuation_20261117/run001'
    scope_receipt = read(scope/'SCOPE_REGISTER_PUBLIC.json', SCOPE_SHA)
    outputs = {x['file']: x['sha256'] for x in scope_receipt['outputs']}
    bases = read(scope/'BASE_SHARD_SCOPE_REGISTER_PRIVATE.json', outputs['BASE_SHARD_SCOPE_REGISTER_PRIVATE.json'])
    base = next(x for x in bases if x['shard_id'] == row['shard_id'])
    mappings = read(R/'source_binding_20261118/run002/DESCRIPTION_TO_BASE_SOURCE_BINDING_PRIVATE.jsonl', MAP_SHA, True)
    binding = next(x for x in mappings if x['shard_id'] == row['shard_id'])
    if binding['status'] != 'source_provenance_bound' or binding['base_artifact_sha256_from_existing_register'] != base['ad_sha256'] or base['ad_rows'] != row['ad_rows']:
        raise ValueError('catalog_base_source_binding_disagrees')
    needed = {base['ad_sha256'], binding['source_sha256_from_cached_receipts']}
    locators = []
    for cluster, c in ledger_handles:
        for path, root, rel, size, status, h in c.execute('select path,root,rel,size,status,sha from files where sha in (?,?)', tuple(sorted(needed))):
            if status == 'verified' and 'batch035' not in path.lower() and PROTECTED not in path:
                locators.append(dict(cluster=cluster, path=path, root=root, rel=rel, size=size, sha256=h))
        c.close()
    if {m['sha256'] for m in locators} != needed: reasons.append('finite_window_source_or_base_ledger_locator_missing')
    end = min(start + 150, row['ad_rows'])
    union_sha = save('KNOWN_CONTEXT_EXCLUSION_UNION_PRIVATE.json', {
        'context_sha256': sorted(excluded), 'policy': 'all_statuses_all_cached_prepared_all_known_exposure_metadata',
        'completeness': 'must_add_existing_10000_reference_hashes_and_confirm_runtime_registry_coverage_before_model_calls',
        'source_pins': pins, 'status_index_relative_path': str(idxp.relative_to(R))})
    window = {'kind': 'finite_canonical_row_window_not_yet_new_context_frame', 'max_new_model_contexts': 150,
        'batch_predecessor': batch, 'preparation_receipt_sha256': receipt_sha, 'manifest_sha256': mh,
        'start_cursor': cursor, 'end_cursor_exclusive': {'shard_ordinal': ordinal, 'row_offset': end},
        'canonical_rows_max': end-start, 'catalog_entry': row, 'base_register_entry': base,
        'description_source_binding': binding, 'verified_existing_ledger_locators': locators,
        'context_exclusion_union_sha256': union_sha,
        'requirements_before_any_model_call': ['confirm comprehensive accepted/reference/exposure/protection hash union',
            'read only these canonical rows and exact SOURCE_ROW complete descriptions on Azure',
            'use pinned full-context normalizer and compare context SHA to full exclusion union',
            'keep fewer than 150 when duplicates, excluded, missing, or incomplete; no silent replacement'],
        'cursor_gate_blockers': sorted(set(reasons)), 'input_metadata_pins': pins}
    window_sha = save('FINITE_SOURCE_WINDOW_PRIVATE.json', window)
    save('MISSING_CACHED_PREPARATION_METADATA_LOCATORS_PRIVATE.json', missing_metadata)
    report = {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'finite_source_window_identified' if not reasons else 'finite_source_window_identified_with_explicit_metadata_gaps',
        'latest_SHA_bound_preparation_batch': batch, 'latest_verified_ledger_preparation_batch': newest_batch,
        'next_cursor': cursor, 'canonical_rows_max': end-start, 'source_window_sha256': window_sha,
        'excluded_unique_contexts': len(excluded), 'status_counts_all_excluded': state_counts,
        'cached_manifests_read': len(manifest_rows), 'protected_metadata_entries_skipped': skipped_protected,
        'missing_metadata_artifacts': len({m['sha256'] for m in missing_metadata}),
        'blockers': sorted(set(reasons)), 'new_context_freshness_certified': False,
        'full_exclusion_completeness_certified': False, 'base_has_context_SHA': False,
        'raw_text_reads': 0, 'base_parquet_reads': 0, 'network_calls': 0, 'model_calls': 0,
        'new_resources': 0, 'protected_payload_reads': 0, **dict(totals)}
    save('FRAME_PROBE_PUBLIC.json', report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__': main()
