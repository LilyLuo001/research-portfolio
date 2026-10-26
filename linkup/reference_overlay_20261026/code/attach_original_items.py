#!/usr/bin/env python3
"""Stream accepted recovered original items/groups onto the accepted KS 10k ad bridge.

This scheduled job reads only the SHA-pinned recovered JSONL and five bridge
columns. It never opens complete advertisement/context text, reconstructs new
labels, joins family-array positions, or changes earlier ad-level measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

ITEMS_SHA = '8a28fa07361c4eb56c6630941a8517c4a25f9766412e7519c34e43c76f71797e'
GROUPS_SHA = '132a6c5c870301b7bee736b66f942a187d7c408eaad466b6ae7cfffc382f11eb'
BRIDGE_SHA = '733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb'
AD_KEY_COLUMNS = ('JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW')
SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
ITEM_FAMILIES = {
    'experience_object': 'experience_clauses',
    'experience_strength': 'experience_clauses',
    'experience_literal_years': 'experience_clauses',
    'qualification_conditions_and_alternatives': 'experience_clauses',
    'entry_wording_and_scope': 'entry_items',
    'current_responsibility_subject_and_relation': 'responsibility_items',
    'technology_category_and_role': 'technology_items',
}
ORPHAN_REASON = 'normalized_context_absent_from_accepted_10000_bridge'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def pinned(path: str, supplied: str, expected: str) -> Path:
    if supplied != expected:
        raise ValueError('input is not the accepted frozen SHA256')
    file = Path(path)
    if sha256(file) != expected:
        raise ValueError(f'input byte SHA256 mismatch: {file}')
    return file


def rows(path: Path):
    with path.open('r', encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f'original JSONL row must be an object: {path}:{number}')
                yield value


def canonical_key(row: dict) -> list:
    key = [row.get(name) for name in AD_KEY_COLUMNS]
    if any(not isinstance(key[i], str) or not key[i] for i in (0, 1)):
        raise ValueError('missing original advertisement string locator')
    if any(type(key[i]) is not int for i in (2, 3)):
        raise ValueError('original advertisement row locator must be integer')
    return key


def compact_key(key: list) -> str:
    return json.dumps(key, ensure_ascii=False, separators=(',', ':'))


def bridge_index(path: Path, expected_ads: int):
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(path)
    columns = ['normalized_context_sha256', *AD_KEY_COLUMNS]
    if any(name not in parquet.schema_arrow.names for name in columns):
        raise ValueError('accepted KS bridge is missing original locator/context columns')
    by_context = defaultdict(list)
    seen_keys = set()
    ad_rows = 0
    for batch in parquet.iter_batches(columns=columns, batch_size=4096):
        for row in batch.to_pylist():
            context = row['normalized_context_sha256']
            if not isinstance(context, str) or not re.fullmatch(r'[0-9a-f]{64}', context):
                raise ValueError('invalid complete normalized-context SHA256 in bridge')
            key = canonical_key(row)
            encoded = compact_key(key)
            if encoded in seen_keys:
                raise ValueError('duplicate four-part original advertisement locator')
            seen_keys.add(encoded)
            by_context[context].append(key)
            ad_rows += 1
    if ad_rows != expected_ads:
        raise ValueError('accepted KS bridge advertisement cardinality changed')
    return by_context, ad_rows


def source_identity(row: dict, kind: str):
    context, split, source_sha = row.get('context_sha256'), row.get('split'), row.get('source_sha256')
    if not isinstance(context, str) or not re.fullmatch(r'[0-9a-f]{64}', context):
        raise ValueError('invalid original item/group context SHA256')
    if split not in SPLITS:
        raise ValueError('invalid original split')
    if not isinstance(source_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', source_sha):
        raise ValueError('invalid original accepted-source SHA256')
    source_id = row.get('source_record_id')
    if source_id is None or isinstance(source_id, (dict, list, bool)):
        raise ValueError('missing original source record identity')
    if row.get('context_ref') != 'CONTEXTS_PRIVATE.jsonl#' + context:
        raise ValueError('original context reference does not bind to context SHA256')
    if kind == 'item':
        family = row.get('field_family')
        if family not in ITEM_FAMILIES:
            raise ValueError('unrecognized original field family')
        path = row.get('original_item_path')
        if not isinstance(path, str) or not re.fullmatch('/' + ITEM_FAMILIES[family] + r'/[0-9]+', path):
            raise ValueError('invalid original same-item path for family')
        if not isinstance(row.get('labels'), dict) or not isinstance(row.get('evidence'), list):
            raise ValueError('missing original labels/evidence')
        if 'accepted_same_item_experience_tuple' in row and not isinstance(row['accepted_same_item_experience_tuple'], dict):
            raise ValueError('invalid original accepted same-item tuple')
        status = 'known'  # Producer emits items only from accepted known family cells.
        identity = (kind, context, split, source_sha, json.dumps(source_id, sort_keys=True), family, path)
    else:
        family = 'qualification_conditions_and_alternatives'
        path = row.get('original_group_path')
        if not isinstance(path, str) or not re.fullmatch(r'/qualification_alternatives/[0-9]+', path):
            raise ValueError('invalid original qualification group path')
        status = row.get('accepted_family_status')
        if status not in ('known', 'not_applicable'):
            raise ValueError('invalid original accepted qualification status')
        if not isinstance(row.get('original_group'), dict) or not isinstance(row.get('evidence'), list):
            raise ValueError('missing original group/evidence')
        identity = (kind, context, split, source_sha, json.dumps(source_id, sort_keys=True), family, path)
    return context, split, family, status, identity


def run(args):
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet job required')
    destination = Path(args.output)
    if destination.exists():
        raise FileExistsError('create-only output already exists')
    items = pinned(args.items, args.items_sha256, ITEMS_SHA)
    groups = pinned(args.groups, args.groups_sha256, GROUPS_SHA)
    bridge = pinned(args.bridge, args.bridge_sha256, BRIDGE_SHA)
    by_context, bridge_ads = bridge_index(bridge, args.expected_bridge_ads)
    destination.mkdir(parents=True, mode=0o700)
    attached_paths = {kind: destination / f'ATTACHED_ORIGINAL_{kind.upper()}S_PRIVATE.jsonl' for kind in ('item','group')}
    orphan_paths = {kind: destination / f'ORPHAN_ORIGINAL_{kind.upper()}S_PRIVATE.jsonl' for kind in ('item','group')}
    source_counts, matched_counts, orphan_counts, expanded_counts = (Counter() for _ in range(4))
    source_contexts, matched_contexts, orphan_contexts, matched_ads = (defaultdict(set) for _ in range(4))
    seen_identity = set()
    for kind, input_path in (('item', items), ('group', groups)):
        attached_path, orphan_path = attached_paths[kind], orphan_paths[kind]
        with attached_path.open('x', encoding='utf-8') as attached, orphan_path.open('x', encoding='utf-8') as orphan:
            os.chmod(attached_path, 0o600)
            os.chmod(orphan_path, 0o600)
            for row in rows(input_path):
                context, split, family, status, identity = source_identity(row, kind)
                if identity in seen_identity:
                    raise ValueError('duplicate original same-source item/group identity')
                seen_identity.add(identity)
                category = (kind, family, split, status)
                source_counts[category] += 1
                source_contexts[category].add(context)
                ads = by_context.get(context)
                if not ads:
                    orphan.write(json.dumps({'source_row':row, 'orphan_reason':ORPHAN_REASON}, ensure_ascii=False, sort_keys=True) + '\n')
                    orphan_counts[category] += 1
                    orphan_contexts[category].add(context)
                    continue
                matched_counts[category] += 1
                matched_contexts[category].add(context)
                for ad_key in ads:
                    attached.write(json.dumps({'canonical_key':ad_key, 'normalized_context_sha256':context,
                        'source_row':row, 'attachment_type':'exact_complete_normalized_context'}, ensure_ascii=False, sort_keys=True) + '\n')
                    expanded_counts[category] += 1
                    matched_ads[category].add(compact_key(ad_key))
    if any(source_counts[category] != matched_counts[category] + orphan_counts[category] for category in source_counts):
        raise RuntimeError('original row conservation failed')

    categories = sorted(source_counts)
    support = []
    for category in categories:
        kind, family, split, status = category
        support.append({'kind':kind, 'field_family':family, 'split':split, 'accepted_family_status':status,
            'source_record_rows':source_counts[category], 'source_contexts':len(source_contexts[category]),
            'matched_source_rows':matched_counts[category], 'matched_contexts':len(matched_contexts[category]),
            'matched_advertisements':len(matched_ads[category]), 'expanded_ad_item_or_group_rows':expanded_counts[category],
            'orphan_source_rows':orphan_counts[category], 'orphan_contexts':len(orphan_contexts[category])})
    outputs = {path.name:sha256(path) for path in [*attached_paths.values(), *orphan_paths.values()]}
    receipt = {'schema':'reference-overlay-original-items-attachment-public-v1',
        'scheduler_job_id':os.environ['SLURM_JOB_ID'], 'code_sha256':sha256(Path(__file__)),
        'input_sha256':{'items':ITEMS_SHA,'groups':GROUPS_SHA,'accepted_ks_10000_bridge':BRIDGE_SHA},
        'bridge_ad_rows':bridge_ads,'bridge_unique_contexts':len(by_context),
        'source_item_rows':sum(n for (kind,_,_,_),n in source_counts.items() if kind == 'item'),
        'source_group_rows':sum(n for (kind,_,_,_),n in source_counts.items() if kind == 'group'),
        'matched_source_rows':sum(matched_counts.values()),
        'orphan_source_rows':sum(orphan_counts.values()),
        'expanded_ad_item_or_group_rows':sum(expanded_counts.values()),
        'unique_matched_contexts':len(set().union(*matched_contexts.values())),
        'unique_orphan_contexts':len(set().union(*orphan_contexts.values())),
        'unique_matched_advertisements':len(set().union(*matched_ads.values())),
        'support_by_source_kind_family_split_status':support,'output_sha256':outputs,
        'orphan_reason':ORPHAN_REASON,
        'binding':'Original item identity is (complete context SHA256, source SHA256, source record ID, original item path, field family); group identity uses original group path. Family-array positions are never cross-family join keys.',
        'evidence_coordinates':'Original recovered quote occurrences remain in their pinned complete normalized-context coordinate system; this job did not read full text or revalidate them.',
        'boundary':'Independent original-clause sidecar for exact accepted 10000-ad context matches. Old ad presence fields and field-family masks are unchanged. No synthetic minimum year, no new labels/recovery/training, no transfer outside this bridge.'}
    receipt_path = destination / 'ORIGINAL_ITEMS_ATTACHMENT_PUBLIC.json'
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({'public_receipt':str(receipt_path),
        'source_item_rows':receipt['source_item_rows'],'source_group_rows':receipt['source_group_rows']}))
    return receipt


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('items','groups','bridge'):
        p.add_argument('--'+name, required=True)
        p.add_argument('--'+name+'-sha256', required=True)
    p.add_argument('--expected-bridge-ads', type=int, default=10000)
    p.add_argument('--output', required=True)
    return p


if __name__ == '__main__':
    run(parser().parse_args())
