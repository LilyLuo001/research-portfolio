"""Bounded, zero-inference diagnostic of saved candidate outputs, not requalification.

Runs only on Azure. Never modifies source reviews, ledgers, schema or old metrics.
Stops on a pin mismatch; protected contexts are skipped before validation.
"""
import collections
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
from field_validation import FIELDS, FieldValidator, parse_review


def main():
    os.umask(0o077)
    start = time.monotonic()
    root = Path.home() / 'migration'
    base = root / 'execution_20261116/run001'
    candidate = base / 'qualification500_v1/luna_revision002'
    output = root / 'measurement_protocol_20261117/shadow001'
    def read(p): return json.loads(p.read_text())
    def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    def immutable(p, value):
        payload = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        if p.exists():
            raise RuntimeError('diagnostic_output_exists_do_not_repeat')
        p.write_bytes(payload)
    if (output / 'SHADOW_DIAGNOSTIC_PUBLIC.json').exists():
        raise RuntimeError('completed_diagnostic_exists')
    expected = read(output / 'PINS_PUBLIC.json')
    bindings = {
        'candidate_status': candidate / 'RUN_STATUS_PUBLIC.json',
        'candidate_frame': candidate / 'INPUTS_PRIVATE.jsonl',
        'candidate_schema': candidate / 'SCHEMA.json',
        'candidate_pins': candidate / 'SHA256SUMS_PRIVATE.json',
        'exclusions': base / 'continuation02/final_checkpoint/RUNTIME_EXCLUSIONS_PRIVATE.json',
        'validator': root / 'code/validate_reviews.py',
        'old_state': base / 'AZURE_RESEARCH_STATE.json',
    }
    for name, p in bindings.items():
        assert sha(p) == expected['inputs'][name], 'input_pin_changed'
    for name, digest in expected['code'].items():
        assert sha(output / name) == digest, 'diagnostic_code_pin_changed'
    protected_sources = [bindings['exclusions'], candidate / 'EXCLUSIONS_PRIVATE.json']
    excluded_hashes, excluded_tasks = set(), set()
    for p in protected_sources:
        e = read(p)
        excluded_hashes.update(e.get('context_sha256', []))
        excluded_tasks.update(e.get('tasks', []))
    status = read(bindings['candidate_status'])
    assert status['status'] == 'finite_benchmark_completed' and status['completed'] == 500
    original_pins = read(bindings['candidate_pins'])
    spec = importlib.util.spec_from_file_location('frozen_validator', bindings['validator'])
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    engine = FieldValidator(read(bindings['candidate_schema']), frozen)
    frame = [json.loads(line) for line in bindings['candidate_frame'].read_text().splitlines() if line.strip()]
    assert len(frame) == 500 and len({str(item['case']) for item in frame}) == 500
    # The existing combined input frame is used to identify exclusions. Never
    # reopen protected result directories or pass their context to the adapter.
    eligible_ordinals = {i for i, item in enumerate(frame) if
        item['row']['context_sha256'] not in excluded_hashes and item['task'] not in excluded_tasks}
    eligible_prefixes = tuple('results/case%04d/' % i for i in sorted(eligible_ordinals))
    checked_result_pins = {rel: digest for rel, digest in original_pins.items()
                           if rel.startswith(eligible_prefixes)}
    for relative, digest in checked_result_pins.items():
        assert not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'unsafe_manifest_path'
        assert (candidate / relative).resolve().is_relative_to(candidate.resolve()), 'source_path_escape'
        assert sha(candidate / relative) == digest, 'eligible_saved_candidate_output_changed'
    counts = collections.Counter()
    previous = collections.Counter()
    per_field = {f: collections.Counter() for f in FIELDS}
    private_diagnostics = []
    for ordinal, item in enumerate(frame):
        row = item['row']
        counts['frame_accounted'] += 1
        if row['context_sha256'] in excluded_hashes or item['task'] in excluded_tasks:
            counts['protected_skipped'] += 1
            continue
        result_dir = candidate / 'results' / ('case%04d' % ordinal)
        assert str((result_dir / 'RESULT_PUBLIC.json').relative_to(candidate)) in checked_result_pins
        old = read(result_dir / 'RESULT_PUBLIC.json')
        previous[old['status']] += 1
        path = result_dir / 'REVIEW_PRIVATE.jsonl'
        if not path.is_file():
            counts['missing_saved_review'] += 1
            continue
        assert str(path.relative_to(candidate)) in checked_result_pins
        try:
            review = parse_review(path.read_text())
        except (ValueError, TypeError):
            counts['unparseable_saved_review'] += 1
            continue
        result = engine.validate(row, review, protected=False)
        counts['saved_reviews_checked'] += 1
        counts[result['status']] += 1
        private_diagnostics.append({'case': str(item['case']), 'split': item['split'],
                                    'original_status': old['status'], 'diagnostic': result})
        gained = 0
        for field, checked in result['fields'].items():
            c = per_field[field]
            c[checked['status']] += 1
            complete = checked.get('field_review_complete', False)
            if not complete:
                c['incomplete_or_shared_failure'] += 1
            if checked['status'] == 'engineering_valid' and complete:
                c['full_known_engineering_valid'] += 1
                if old['status'] != 'frozen_validator_pass_candidate_only':
                    c['full_known_from_legacy_invalid'] += 1
                    gained += 1
            if checked['status'] == 'reviewed_unknown' and complete:
                c['full_reviewed_unknown'] += 1
            c['checked_quote_instances'] += checked.get('checked_quote_instances', 0)
        counts['legacy_invalid_records_with_at_least_one_full_known_field'] += gained > 0
    assert counts['frame_accounted'] == 500
    assert counts['protected_skipped'] + counts['missing_saved_review'] + counts['unparseable_saved_review'] + counts['saved_reviews_checked'] == 500
    for name, p in bindings.items():
        assert sha(p) == expected['inputs'][name], 'source_changed_during_diagnostic'
    for relative, digest in checked_result_pins.items():
        assert sha(candidate / relative) == digest, 'eligible_saved_output_changed_during_diagnostic'
    private_path = output / 'FIELD_DIAGNOSTIC_PRIVATE.json'
    immutable(private_path, private_diagnostics)
    report = {
        'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'saved_output_shadow_diagnostic_complete',
        'wall_seconds': time.monotonic() - start,
        'scope': 'same500_saved_Luna_outputs_diagnostic_only_not_independent_validation',
        'counts': dict(counts), 'previous_status_counts_eligible_only': dict(previous),
        'per_field': {f: dict(c) for f, c in per_field.items()},
        'new_model_calls': 0, 'new_accepted_records': 0, 'new_qualified_fields': 0,
        'checked_eligible_outputs_and_control_pins_unchanged': True, 'runtime_policy_changed': False,
        'protected_output_files_opened': 0,
        'combined_source_frame_read_for_identity_filtering': True,
        'partial_fields_never_counted_as_full_known': True,
        'protected_skipped_before_review_access': True,
        'not_semantic_accuracy_or_paraphrase_reassessment': True,
        'private_diagnostic_sha256': sha(private_path),
        'output_relative_to_migration': 'measurement_protocol_20261117/shadow001',
    }
    immutable(output / 'SHADOW_DIAGNOSTIC_PUBLIC.json', report)
    immutable(output / 'SHA256SUMS_PUBLIC.json', {n: sha(output / n) for n in
        ['field_validation.py', 'cloud_shadow_diagnostic.py', 'PINS_PUBLIC.json',
         'FIELD_DIAGNOSTIC_PRIVATE.json', 'SHADOW_DIAGNOSTIC_PUBLIC.json']})
    compact = {k: report[k] for k in ['status', 'wall_seconds', 'counts', 'new_model_calls',
                                    'new_accepted_records', 'checked_eligible_outputs_and_control_pins_unchanged']}
    compact['full_known_from_legacy_invalid_by_field'] = {
        f: c.get('full_known_from_legacy_invalid', 0) for f, c in per_field.items()}
    compact['public_report_sha256'] = sha(output / 'SHADOW_DIAGNOSTIC_PUBLIC.json')
    print(json.dumps(compact))


if __name__ == '__main__':
    main()
