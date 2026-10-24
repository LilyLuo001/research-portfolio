#!/usr/bin/env python3
"""Scheduled SCNet metadata inventory only; never open context/text/source packets.

Required recovered filenames are exactly those emitted by materialize_supervision.py.
Supply their receipt-bound SHA256s. --input-manifest is the unchanged recovery
manifest; only its freeze, frozen ledger/isolation/holdout and legacy adapter are
read. No original reviews, frame parquet, packets, rules or model are opened.
Output is create-only, aggregate-only. Original item/group IDs remain in memory.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path

SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
FINAL_SHA = '5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1'
STRENGTH = 'experience_strength'
QUAL = 'qualification_conditions_and_alternatives'
RESP = 'current_responsibility_subject_and_relation'
FIELDS = {
    STRENGTH: ('object', 'strength'),
    QUAL: ('object', 'conditionality', 'alternative_group', 'alternative_branch'),
    RESP: ('dimension', 'subject', 'relation', 'conditionality'),
}
# Public values are limited to existing enum values, never names/local group IDs.
ENUMS = {
    'object': {'general_work', 'industry_domain', 'occupation_task', 'tool_specific'},
    'strength': {'required', 'preferred', 'explicitly_waived', 'unspecified'},
    'conditionality': {'conditional', 'unconditional', 'unspecified'},
    'dimension': {'client_ownership', 'independent_judgment', 'people_supervision', 'training_mentoring'},
    'subject': {'advertised_worker', 'employer_general', 'other_employee'},
    'relation': {'current_duty', 'employer_description', 'other_person', 'prior_experience', 'required_capability'},
}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def checked(spec):
    if sha(spec['path']) != spec['sha256']:
        raise RuntimeError('input SHA mismatch')
    return Path(spec['path'])


def rows(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def public_value(key, value):
    if value is None:
        return 'original_null_not_negative'
    return value if isinstance(value, str) and value in ENUMS[key] else 'other_original_value_private'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('recovered', 'items-sha256', 'groups-sha256', 'input-manifest', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet Slurm job required')
    output = Path(a.output)
    if output.exists():
        raise RuntimeError('output must be new')
    manifest = json.loads(Path(a.input_manifest).read_text())
    freeze = json.loads(checked(manifest['freeze']).read_text())
    inputs = freeze['inputs']
    if inputs['holdout']['sha256'] != FINAL_SHA:
        raise RuntimeError('original final holdout changed')
    final = {r['normalized_context_sha256'] for r in rows(checked(inputs['holdout']))}
    if len(final) != 1331:
        raise RuntimeError('original final holdout cardinality changed')
    isolated = {r['normalized_context_sha256'] for r in rows(checked(inputs['isolation']))}
    spec = importlib.util.spec_from_file_location('frozen_legacy', checked(inputs['legacy']))
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)

    def split(context):
        return SPLITS[1] if context in final else SPLITS[2] if legacy.is_holdout(context) else SPLITS[0]

    masks, signatures = {}, {}
    counts = Counter()
    support = defaultdict(set)
    item_keys = Counter()
    for cell in rows(checked(inputs['ledger'])):
        c, family = cell['normalized_context_sha256'], cell['field_family']
        if family not in FIELDS and family != 'experience_object':
            continue
        identity = (c, family)
        prov = [{k: v for k, v in x.items() if k != 'binding_mode'} for x in cell.get('provenance', [])]
        signature = json.dumps([cell['status'], cell.get('structured_value'), prov], sort_keys=True)
        if identity in signatures:
            if signatures[identity] != signature:
                raise RuntimeError('inconsistent duplicate acceptance mask')
            continue
        signatures[identity] = signature
        masks[identity] = cell
        s = split(c)
        # States are existing bounded schema enums, not negative labels.
        state = cell['status']
        if state not in {'known', 'not_applicable', 'unknown_or_conflict', 'candidate_only', 'partial'}:
            state = 'other_original_state'
        counts[('family_mask', family, state, s)] += 1
        counts[('isolated_mask', family, str(c in isolated), s)] += 1

    def accept(r, family):
        c = r['context_sha256']
        if r['split'] != split(c) or c in isolated:
            raise RuntimeError('split or isolation violation')
        cell = masks.get((c, family))
        prov = cell.get('provenance', []) if cell else []
        if not cell or cell['status'] != 'known' or len(prov) != 1:
            raise RuntimeError('recovered item acceptance mask violation')
        v = prov[0]
        if (v.get('source_sha256'), str(v.get('source_record_id')), v.get('source_context_sha256')) != (
                r['source_sha256'], str(r['source_record_id']), c):
            raise RuntimeError('recovered item original-source binding violation')

    def identity(r):
        return (r['context_sha256'], r['source_sha256'], str(r['source_record_id']), r['original_item_path'])

    recovered = Path(a.recovered)
    item_path = checked({'path': str(recovered / 'RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl'), 'sha256': a.items_sha256})
    group_path = checked({'path': str(recovered / 'QUALIFICATION_GROUPS_PRIVATE.jsonl'), 'sha256': a.groups_sha256})
    items = {}
    for r in rows(item_path):
        family = r['field_family']
        if family not in FIELDS and family != 'experience_object':
            continue
        accept(r, family)
        key = (family, identity(r))
        if key in items:
            raise RuntimeError('duplicate recovered family/item')
        items[key] = r
        if family not in FIELDS:
            continue
        s, c, labels = r['split'], r['context_sha256'], r['labels']
        counts[('items', family, 'accepted', s)] += 1
        counts[('pair_endpoint_readiness', family, str(bool(r.get('entity_pair_ready'))), s)] += 1
        # Schema key inventory only; never emit original values/quotes/IDs.
        for k in r['original_item_audit_only']:
            item_keys[(family, k, s)] += 1
        for k in FIELDS[family]:
            if k in ('alternative_group', 'alternative_branch'):
                value = 'present' if labels.get(k) is not None else 'original_null_not_negative'
            else:
                value = public_value(k, labels.get(k))
            counts[('field', family + ':' + k, value, s)] += 1
            support[(family + ':' + k, value, s)].add(c)
        if any(value == 'no_relation' for value in labels.values() if isinstance(value, str)):
            counts[('explicit_original_enum', family, 'no_relation', s)] += 1
        if family == RESP:
            value = '|'.join(public_value(k, labels.get(k)) for k in FIELDS[RESP])
            support[('same_item_dimension_subject_relation_conditionality', value, s)].add(c)

    for (family, ident), r in items.items():
        if family != STRENGTH:
            continue
        obj, qual = items.get(('experience_object', ident)), items.get((QUAL, ident))
        ok = obj is not None and qual is not None and obj['labels']['object'] == r['labels']['object'] == qual['labels']['object']
        s, c = r['split'], r['context_sha256']
        counts[('same_item_scope', STRENGTH, 'accepted_object_and_qualification' if ok else 'incomplete_binding', s)] += 1
        if ok:
            values = '|'.join(public_value(k, v) for k, v in (
                ('object', r['labels']['object']), ('strength', r['labels']['strength']),
                ('conditionality', qual['labels']['conditionality'])))
            support[('same_item_object_strength_conditionality', values, s)].add(c)

    groups = {}
    for r in rows(group_path):
        c, s, group = r['context_sha256'], r['split'], r['original_group']
        if s != split(c) or c in isolated:
            raise RuntimeError('group split/isolation violation')
        cell = masks.get((c, QUAL))
        if not cell or cell['status'] not in ('known', 'not_applicable') or r['accepted_family_status'] != cell['status']:
            raise RuntimeError('group mask violation')
        prov = cell.get('provenance', [])
        if len(prov) != 1 or (prov[0].get('source_sha256'), str(prov[0].get('source_record_id')), prov[0].get('source_context_sha256')) != (r['source_sha256'], str(r['source_record_id']), c):
            raise RuntimeError('group original-source binding violation')
        key = (c, r['source_sha256'], str(r['source_record_id']), group['group'])
        if key in groups:
            raise RuntimeError('duplicate original group')
        groups[key] = group
        relation = group['relation']
        if relation not in ('OR', 'AND'):
            raise RuntimeError('unexpected recovered group relation')
        counts[('groups', QUAL, relation, s)] += 1
        counts[('group_branches', QUAL, relation, s)] += len(group['branches'])
        support[('original_group_relation', relation, s)].add(c)
    for (family, _), r in items.items():
        if family != QUAL:
            continue
        labels = r['labels']
        gid, bid = labels.get('alternative_group'), labels.get('alternative_branch')
        group = groups.get((r['context_sha256'], r['source_sha256'], str(r['source_record_id']), gid)) if gid is not None else None
        state = ('null_group_not_negative' if gid is None else 'group_unavailable' if group is None else
                 'shared_condition_null_branch_not_negative' if bid is None else
                 'explicit_branch_bound' if sum(b['branch'] == bid for b in group['branches']) == 1 else 'branch_binding_unresolved')
        counts[('branch_binding', QUAL, state, r['split'])] += 1
        support[('existing_branch_binding_state', state, r['split'])].add(r['context_sha256'])

    report = {
        'version': 'relation-channel-metadata-inventory-v1', 'scheduler_job_id': os.environ['SLURM_JOB_ID'],
        'code_sha256': sha(__file__), 'input_manifest_sha256': sha(a.input_manifest),
        'recovered_items_sha256': a.items_sha256, 'qualification_groups_sha256': a.groups_sha256,
        'counts': [dict(kind=k, task=t, value=v, split=s, count=n) for (k, t, v, s), n in sorted(counts.items())],
        'original_item_schema_key_counts': [dict(family=f, key=k, split=s, items=n) for (f, k, s), n in sorted(item_keys.items())],
        'support': [dict(task=t, value=v, split=s, unique_contexts=len(cs)) for (t, v, s), cs in sorted(support.items())],
        'support_gate': [dict(task=t, value=v, train=len(support.get((t, v, SPLITS[0]), set())),
                              final_previously_exposed=len(support.get((t, v, SPLITS[1]), set())),
                              train50_final50_pass=len(support.get((t, v, SPLITS[0]), set())) >= 50 and len(support.get((t, v, SPLITS[1]), set())) >= 50)
                         for t, v in sorted({(t, v) for t, v, s in support})],
        'generated_labels': 0, 'generated_negatives': 0, 'body_or_context_files_opened': 0,
        'original_schema_pair_negative_annotation_field': False,
        'decision': 'inventory_only_no_training_or_production_qualification',
        'limitations': ['Known/not_applicable/null/unlabeled are never pair negatives.',
                       'Schema key counts and explicit no_relation enum counts do not manufacture pair endpoints.',
                       'Marginal and same-item supports are not candidate binding or end-to-end accuracy.',
                       'All noncore original enum values are retained privately in inputs, aggregated as other_original_value_private.'],
    }
    output.mkdir(parents=True, mode=0o700)
    with open(output / 'RELATION_METADATA_PUBLIC.json', 'x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()
