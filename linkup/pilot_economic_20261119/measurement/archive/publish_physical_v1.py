"""Cloud-only field-local release and 100% physical-row projection. No inference.

Retains missing/unknown and links private detailed results without certifying
their relation atoms. A physical row is never dropped because extraction failed.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, value, jsonl=False):
    data = (''.join(json.dumps(x, ensure_ascii=False, sort_keys=True) + '\n' for x in value)
            if jsonl else json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
    path.chmod(0o600)
    return hashlib.sha256(data).hexdigest()


def project(args):
    started = time.monotonic()
    root = args.directory.resolve()
    policy = read(root / 'policy.json')
    release = read(root / 'measurement/ECONOMIC_RELEASE_PUBLIC.json')
    assert release['released_measure_ids'] == policy['released_measure_ids']
    for path, digest in ((args.scorer, args.scorer_sha256), (args.frozen_validator, args.frozen_validator_sha256)):
        assert sha(path) == digest
    scorer = module(args.scorer, 'economic_projection_frozen_scorer')
    frozen = module(args.frozen_validator, 'economic_projection_frozen_validator')
    specs = [x['spec'] for x in release['released_measures']]
    manifests = []
    inputs, physical = {}, []
    for folder in sorted((root / 'preparation').glob('batch*')):
        file = folder / 'BATCH_MANIFEST_PUBLIC.json'
        if not file.exists():
            continue
        m = read(file)
        for key in ('inputs', 'physical_rows', 'exclusions'):
            assert sha(folder / m['filenames'][key]) == m[key + '_sha256']
        if manifests:
            assert m['previous_batch_manifest_sha256'] == manifests[-1]['sha256']
        manifests.append({'batch_id': m['batch_id'], 'sha256': sha(file)})
        for item in lines(folder / m['filenames']['inputs']):
            h = item['row']['context_sha256']
            assert h not in inputs
            assert hashlib.sha256(item['row']['full_document'].encode()).hexdigest() == h
            inputs[h] = item
        physical.extend(lines(folder / m['filenames']['physical_rows']))
        if folder.name == args.through_batch:
            break
    assert manifests[-1]['batch_id'] == args.through_batch
    assert len(physical) == m['cumulative_physical_rows']
    assert len(set(x['physical_row_id'] for x in physical)) == len(physical)
    db = sqlite3.connect((root / 'ADMISSION_PRIVATE.sqlite3').as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    attempts = [dict(x) for x in db.execute('SELECT * FROM attempts ORDER BY id')]
    db.close()
    latest = {(x['leg'], x['context']): x for x in attempts}
    contexts, observations = [], {}
    for h, item in inputs.items():
        attempt = latest.get(('Luna', h))
        carrier, digest = None, None
        if attempt and attempt['result_path']:
            path = (root / attempt['result_path']).resolve()
            assert path.is_relative_to(root) and sha(path) == attempt['result_sha']
            carrier, digest = read(path), attempt['result_sha']
            assert carrier['context_sha256'] == h
        text = item['row']['full_document']
        units = scorer.source_units(text)
        measures = {}
        for spec in specs:
            observed = scorer.observe(
                carrier.get('payload') if carrier else None,
                carrier.get('field_validation', {}) if carrier else {},
                spec, item['row'], units, frozen,
                processing_status=carrier.get('status', 'unprocessed') if carrier else 'unprocessed')
            outcome = observed['outcome']
            known = observed['status'] == 'known' and outcome in ('present', 'not_mentioned')
            measures[spec['id']] = {
                'value': (1 if outcome == 'present' else 0) if known else None,
                'status': 'provisional_economic_use_user_authorized' if known else observed['status'],
                'source_observation_status': observed['status'],
                'outcome': outcome,
                'binary_only': True,
                'structured_atoms_status': 'saved_unverified',
            }
        entry = {'context_sha256': h, 'measurements': measures, 'result_sha256': digest,
                 'result_status': carrier.get('status') if carrier else 'unprocessed',
                 'policy_sha256': sha(root / 'policy.json')}
        contexts.append(entry)
        observations[h] = entry
    output, states, field_counts = [], Counter(), {x['id']: Counter() for x in specs}
    for mapping in physical:
        h = mapping['context_sha256']
        observed = observations.get(h)
        # protected/old rows retain their original state even if another mapping
        # references the same hash: no automatic promotion of protected output.
        eligible = mapping['state'] in ('new_context_prepared', 'duplicate_context')
        row = {'physical_mapping': mapping, 'policy_sha256': sha(root / 'policy.json'),
               'semantic_context_result': observed if eligible else None,
               'semantic_status': (observed['result_status'] if observed else 'unprocessed') if eligible else mapping['state'],
               'old_result_overwritten': False,
               'CPU_rules_join_key': h if eligible else None,
               'CPU_rules_status': 'separate_versioned_candidate_sidecar' if eligible else 'prior_state_retained_no_reextract'}
        states[row['semantic_status']] += 1
        for spec in specs:
            value = observed['measurements'][spec['id']]['value'] if observed and eligible else None
            field_counts[spec['id']]['unknown' if value is None else str(value)] += 1
        output.append(row)
    args.output.mkdir(parents=True, exist_ok=False)
    hashes = {
        'CONTEXT_MEASUREMENTS_PRIVATE.jsonl': write(args.output / 'CONTEXT_MEASUREMENTS_PRIVATE.jsonl', contexts, True),
        'PHYSICAL_INCREMENT_PRIVATE.jsonl': write(args.output / 'PHYSICAL_INCREMENT_PRIVATE.jsonl', output, True)}
    receipt = {'status': 'versioned_physical_projection_complete', 'through_batch': args.through_batch,
               'physical_rows': len(output), 'unique_new_contexts_prepared': len(inputs),
               'physical_row_conservation': len(output) == len(physical), 'mapping_coverage': 1.0,
               'semantic_physical_state_counts': dict(states), 'field_physical_counts': field_counts,
               'sha256': hashes, 'source_manifests': manifests,
               'policy_sha256': sha(root / 'policy.json'),
               'old_outputs_changed': False, 'model_calls': 0,
               'structured_relation_atoms_certified': False, 'population_accuracy_claimed': False,
               'elapsed_seconds': time.monotonic() - started}
    write(args.output / 'PHYSICAL_PROJECTION_PUBLIC.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'field_physical_counts'}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--through-batch', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--scorer', type=Path, required=True)
    p.add_argument('--scorer-sha256', required=True)
    p.add_argument('--frozen-validator', type=Path, required=True)
    p.add_argument('--frozen-validator-sha256', required=True)
    project(p.parse_args())


if __name__ == '__main__':
    main()
