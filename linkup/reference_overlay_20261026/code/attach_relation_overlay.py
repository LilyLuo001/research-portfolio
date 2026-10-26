#!/usr/bin/env python3
"""Attach the frozen Pro candidate judgments to an accepted ad/context bridge.

Scheduled-compute module. Reads no advertisement or complete-context text. The
original checkpoint verified quotes and offsets against full contexts; this job
checks identity and membership only and does not repeat semantic review.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path

SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
STATUSES = ('resolved', 'explicit_non_experience', 'unknown')
OBJECTS = {'general_work', 'industry_domain', 'occupation_task', 'tool_specific'}
EXPECTED = {
    'train': {'resolved': 618, 'explicit_non_experience': 1341, 'unknown': 220},
    'final_previously_exposed': {'resolved': 142, 'explicit_non_experience': 264, 'unknown': 58},
    'previous_holdout_reserved_not_final': {'resolved': 41, 'explicit_non_experience': 39, 'unknown': 13},
}
EXPECTED_TOTAL = 2736
EXPECTED_CONTEXTS = 1659
CHECKPOINT_LEDGER_SHA = '9ea1fcd0f61182d2d125b19d90af820f549e77351ff1064320613c311ae0d8a9'
CHECKPOINT_MANIFEST_SHA = '16883e6dfee6e2c309a3c98d4c6d87a21dbcccc5029fc8f8cbce1b666c369533'
ACCEPTED_BRIDGE_SHA = '733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb'
AD_KEY_COLUMNS = ('JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW')
FROZEN_INPUT_SHA = {
    'candidates': 'f331e446648b0842fa04860efa170ba58eb9eba0a01444623b83fe7af2f11ac7',
    'candidate_map': 'e360ea8f03be6db0ca30eba490e9eb605ca0f27c3965dc3d6433f7595517bd95',
    'context_states': 'b774fb5927c23fd22a9cd79aa7de683ec9f3ae979b749b6626ef4730aa8ea6f3',
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def checked(path: str, digest: str) -> Path:
    source = Path(path)
    if len(digest) != 64 or file_sha256(source) != digest:
        raise ValueError(f'SHA256 mismatch: {source}')
    return source


def jsonl(path: Path):
    with path.open('r', encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f'JSON object required: {path}:{number}')
                yield value


def key_json(value) -> str:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('original advertisement key must have four ordered parts')
    if any(not isinstance(value[i], str) or not value[i] for i in (0, 1)):
        raise ValueError('original advertisement string key part missing')
    if any(type(value[i]) is not int for i in (2, 3)):
        raise ValueError('original advertisement row key part is not an integer')
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def evidence_shape(items):
    if not isinstance(items, list):
        raise ValueError('evidence list required')
    for evidence in items:
        if not isinstance(evidence, dict):
            raise ValueError('evidence object required')
        start, end, quote = (evidence.get(k) for k in ('start', 'end', 'quote'))
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            raise ValueError('invalid original-context evidence offsets')
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError('missing original evidence quote')


def read_bridge(path: Path, fmt: str):
    if fmt == 'jsonl':
        yield from jsonl(path)
    elif fmt == 'parquet':
        import pyarrow.parquet as pq
        parquet = pq.ParquetFile(path)
        names = parquet.schema_arrow.names
        columns = ['normalized_context_sha256', *AD_KEY_COLUMNS]
        if any(name not in names for name in columns):
            raise ValueError('bridge columns missing')
        for batch in parquet.iter_batches(columns=columns, batch_size=4096):
            yield from batch.to_pylist()
    else:
        raise ValueError('unsupported bridge format')


def prepare(args):
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('scheduled cluster job required')
    root = Path(args.output)
    if root.exists():
        raise FileExistsError(f'create-only output exists: {root}')
    if args.ledger_sha256 != CHECKPOINT_LEDGER_SHA:
        raise ValueError('ledger is not the final accepted checkpoint')
    if args.checkpoint_manifest_sha256 != CHECKPOINT_MANIFEST_SHA:
        raise ValueError('wrong original packet manifest receipt')
    if args.bridge_sha256 != ACCEPTED_BRIDGE_SHA:
        raise ValueError('wrong accepted 10000-ad bridge SHA256 receipt')
    for name, digest in FROZEN_INPUT_SHA.items():
        if getattr(args, name + '_sha256') != digest:
            raise ValueError(f'wrong frozen {name} SHA256 receipt')
    paths = {name: checked(getattr(args, name), getattr(args, name + '_sha256')) for name in
             ('ledger', 'candidates', 'candidate_map', 'context_states', 'bridge')}

    states = {}
    for row in jsonl(paths['context_states']):
        context = row['context_sha256']
        if context in states or row['split'] not in SPLITS:
            raise ValueError('duplicate or invalid original context state')
        states[context] = row

    candidates = {}
    for row in jsonl(paths['candidates']):
        cid, context = row['candidate_id'], row['context_sha256']
        start, end = row['entity_start'], row['entity_end']
        if cid in candidates or context not in states or row['split'] != states[context]['split']:
            raise ValueError('original candidate identity/context/split mismatch')
        if type(start) is not int or type(end) is not int or not 0 <= start < end:
            raise ValueError('invalid frozen candidate offsets')
        expected_id = hashlib.sha256(f'{context}|{start}|{end}'.encode('utf-8')).hexdigest()
        if cid != expected_id:
            raise ValueError('frozen candidate ID hash mismatch')
        candidates[cid] = row

    packet_map = {}
    for row in jsonl(paths['candidate_map']):
        cid = row['candidate_id']
        if cid in packet_map:
            raise ValueError('duplicate immutable packet-map candidate')
        packet_map[cid] = row
    if len(packet_map) != EXPECTED_TOTAL:
        raise ValueError('immutable candidate-map count changed')

    ledger = {}
    status_counts = Counter()
    for row in jsonl(paths['ledger']):
        cid = row['candidate_id']
        if cid in ledger or cid not in candidates or cid not in packet_map:
            raise ValueError('duplicate or unbound reviewed candidate')
        old, mapped = candidates[cid], packet_map[cid]
        for field in ('candidate_id', 'context_sha256', 'split'):
            if row[field] != old[field] or row[field] != mapped[field]:
                raise ValueError('ledger/candidate/map identity mismatch')
        for field in ('entity_start', 'entity_end'):
            if old[field] != mapped[field]:
                raise ValueError('candidate/map numeric offset mismatch')
        context, split, status = row['context_sha256'], row['split'], row['review_status']
        state = states[context]
        if not state['inventory_eligible'] or any(state[k] not in ('known', 'not_applicable') for k in ('year_family_status', 'object_family_status')):
            raise ValueError('reviewed candidate outside original eligible masks')
        if split not in SPLITS or status not in STATUSES or not isinstance(row.get('relations'), list):
            raise ValueError('invalid original split or reviewed status')
        relations = row['relations']
        if status == 'resolved':
            if not relations:
                raise ValueError('resolved review has no relations')
            for relation in relations:
                if not isinstance(relation, dict) or relation.get('object') not in OBJECTS:
                    raise ValueError('unrecognized relation object')
                evidence_shape(relation.get('evidence'))
                if not relation['evidence']:
                    raise ValueError('resolved relation lacks evidence')
        else:
            if relations:
                raise ValueError('unresolved/non-experience review has relations')
            if status == 'explicit_non_experience':
                evidence_shape(row.get('evidence'))
                if not row['evidence'] or not isinstance(row.get('reason'), str) or not row['reason'].strip():
                    raise ValueError('explicit non-experience lacks reason or evidence')
            elif not isinstance(row.get('unknown_reason'), str) or not row['unknown_reason'].strip():
                raise ValueError('unknown lacks insufficiency reason')
        # No complete text is loaded. Text/quote equality and numeric containment
        # were already checked in checkpoint 47393594 against this pinned ledger.
        ledger[cid] = row
        status_counts[(split, status)] += 1
    if len(ledger) != EXPECTED_TOTAL or len({x['context_sha256'] for x in ledger.values()}) != EXPECTED_CONTEXTS:
        raise ValueError('final ledger candidate/context membership changed')
    if any(status_counts[(split, status)] != EXPECTED[split][status] for split in SPLITS for status in STATUSES):
        raise ValueError('final checkpoint status/split counts changed')
    if set(ledger) != set(packet_map):
        raise ValueError('review ledger and immutable packet map differ')

    bridge_by_context = defaultdict(list)
    seen_ad_keys = {}
    bridge_rows = 0
    for row in read_bridge(paths['bridge'], args.bridge_format):
        context = row.get('normalized_context_sha256')
        ad_key = [row.get(name) for name in AD_KEY_COLUMNS]
        if not isinstance(context, str) or len(context) != 64:
            raise ValueError('invalid bridge normalized context SHA256')
        normalized_key = key_json(ad_key)
        if normalized_key in seen_ad_keys:
            raise ValueError('duplicate original advertisement key in bridge')
        seen_ad_keys[normalized_key] = context
        bridge_by_context[context].append(ad_key)
        bridge_rows += 1
    if bridge_rows != args.expected_bridge_ads:
        raise ValueError('accepted bridge advertisement cardinality changed')

    return paths, root, ledger, candidates, packet_map, bridge_by_context, status_counts, bridge_rows


def run(args):
    paths, root, ledger, candidates, packet_map, bridge, status_counts, bridge_rows = prepare(args)
    root.mkdir(parents=True, mode=0o700)
    attached_path = root / 'ATTACHED_RELATIONS_PRIVATE.jsonl'
    orphan_path = root / 'ORPHAN_CANDIDATES_PRIVATE.jsonl'
    matched_ids, orphan_ids, matched_contexts, matched_ads = set(), set(), set(), set()
    attached_counts, orphan_counts = Counter(), Counter()
    matched_candidate_counts = Counter()
    status_contexts, status_ads = defaultdict(set), defaultdict(set)
    with attached_path.open('x', encoding='utf-8') as attached, orphan_path.open('x', encoding='utf-8') as orphan:
        os.chmod(attached_path, 0o600)
        os.chmod(orphan_path, 0o600)
        for cid, review in ledger.items():
            context, split, status = review['context_sha256'], review['split'], review['review_status']
            old, mapped = candidates[cid], packet_map[cid]
            common = dict(candidate_id=cid, context_sha256=context, split=split,
                          entity_start=old['entity_start'], entity_end=old['entity_end'],
                          term=old['term'], review=review,
                          original_packet_id=mapped['packet_id'],
                          evidence_coordinate_system='pinned_complete_normalized_context_python_unicode_half_open',
                          original_checkpoint_job_id='47393594',
                          original_checkpoint_ledger_sha256=CHECKPOINT_LEDGER_SHA)
            ads = bridge.get(context, [])
            if not ads:
                orphan.write(json.dumps(dict(common, orphan_reason='normalized_context_absent_from_accepted_ad_bridge'), ensure_ascii=False, sort_keys=True) + '\n')
                orphan_ids.add(cid)
                orphan_counts[(split, status)] += 1
                continue
            matched_ids.add(cid)
            matched_contexts.add(context)
            matched_candidate_counts[(split, status)] += 1
            status_contexts[(split, status)].add(context)
            for ad_key in ads:
                attached.write(json.dumps(dict(common, canonical_key=ad_key), ensure_ascii=False, sort_keys=True) + '\n')
                matched_ads.add(key_json(ad_key))
                status_ads[(split, status)].add(key_json(ad_key))
                attached_counts[(split, status)] += 1
    if len(matched_ids | orphan_ids) != EXPECTED_TOTAL or matched_ids & orphan_ids:
        raise RuntimeError('candidate conservation failed')
    receipt = dict(schema='reference-overlay-attachment-public-v1', scheduler_job_id=os.environ['SLURM_JOB_ID'],
                   scope='Existing 2736 frozen numeric-duration candidates linked to accepted original advertisement keys by exact normalized complete-context SHA256 only.',
                   code_sha256=file_sha256(Path(__file__)),
                   input_sha256={name: getattr(args, name + '_sha256') for name in paths},
                   checkpoint_packet_manifest_sha256=CHECKPOINT_MANIFEST_SHA,
                   original_checkpoint_job_id='47393594',
                   original_evidence_validation='Inherited from structural checkpoint 47393594. This attachment did not read complete text or recheck quote equality/semantic correctness.',
                   bridge_ad_rows=bridge_rows, bridge_unique_contexts=len(bridge),
                   reviewed_candidates=EXPECTED_TOTAL, reviewed_contexts=EXPECTED_CONTEXTS,
                   unique_matched_candidates=len(matched_ids), unique_orphan_candidates=len(orphan_ids),
                   unique_matched_contexts=len(matched_contexts), unique_matched_advertisements=len(matched_ads),
                   expanded_ad_candidate_rows=sum(attached_counts.values()),
                   status_counts={split: {status: status_counts[(split,status)] for status in STATUSES} for split in SPLITS},
                   matched_candidates_by_split_status={split: {status: matched_candidate_counts[(split,status)] for status in STATUSES} for split in SPLITS},
                   matched_contexts_by_split_status={split: {status: len(status_contexts[(split,status)]) for status in STATUSES} for split in SPLITS},
                   matched_ads_by_split_status={split: {status: len(status_ads[(split,status)]) for status in STATUSES} for split in SPLITS},
                   attached_rows_by_split_status={split: {status: attached_counts[(split,status)] for status in STATUSES} for split in SPLITS},
                   orphan_candidates_by_split_status={split: {status: orphan_counts[(split,status)] for status in STATUSES} for split in SPLITS},
                   orphan_reason='normalized_context_absent_from_accepted_ad_bridge',
                   output_sha256={attached_path.name:file_sha256(attached_path),orphan_path.name:file_sha256(orphan_path)},
                   boundary='Candidate-specific reference overlay only. Non-experience cannot negate an advertisement. Original labels, unknowns, family masks and evidence coordinates are unchanged. No new review, training or corpus inference.')
    receipt_path = root / 'ATTACHMENT_PUBLIC.json'
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'public_receipt':str(receipt_path),'matched_candidates':len(matched_ids),'orphan_candidates':len(orphan_ids)}))
    return receipt


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('ledger', 'candidates', 'candidate-map', 'context-states', 'bridge'):
        p.add_argument('--' + name, required=True)
        p.add_argument('--' + name + '-sha256', required=True)
    p.add_argument('--checkpoint-manifest-sha256', required=True)
    p.add_argument('--bridge-format', required=True, choices=('jsonl','parquet'))
    p.add_argument('--expected-bridge-ads', type=int, default=10000)
    p.add_argument('--output', required=True)
    return p


if __name__ == '__main__':
    run(parser().parse_args())
