"""Post-run, read-only model-reference diagnostics; never a quality promotion.

Only completed, SHA-pinned finite outputs may be compared. Failed/protected
response bodies are not parsed. All comparisons are exact JSON diagnostics,
not semantic truth, precision, recall or population accuracy.
"""
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path

SCHEMA_SHA = 'fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e'
OUTCOMES = ('experience_outcomes', 'entry_outcomes', 'responsibility_outcomes')
ARRAYS = ('experience_clauses', 'qualification_alternatives', 'entry_items',
          'responsibility_items', 'technology_items')
IDENTITY = {'record_id', 'context_sha256'}


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value, *, strip_quotes=False):
    """Preserve all business values; only the diagnostic view omits quotes.

    Numeric 5 and 5.0 compare equally. No lowercasing, synonym matching,
    branch relabeling or removal of objects/years/strength is performed.
    """
    if isinstance(value, dict):
        return {k: canonical(v, strip_quotes=strip_quotes)
                for k, v in sorted(value.items()) if not (strip_quotes and k == 'quotes')}
    if isinstance(value, list):
        return [canonical(v, strip_quotes=strip_quotes) for v in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def array_exact(reference, candidate, *, strip_quotes=False):
    """Top-level multiset comparison retains duplicate counts and nested order."""
    def counts(values):
        return collections.Counter(json.dumps(canonical(v, strip_quotes=strip_quotes),
                                              sort_keys=True, ensure_ascii=False)
                                   for v in values)
    ref, cand = counts(reference), counts(candidate)
    return {'reference_items': len(reference), 'candidate_items': len(candidate),
            'matched_exact_items': sum((ref & cand).values()), 'array_multiset_exact': ref == cand}


def unknown_paths(schema, value, path=''):
    """Only declared enum unknown/unresolved states, never free-text words."""
    found = []
    if 'enum' in schema and value in ('unknown', 'unresolved'):
        found.append(path)
    if schema.get('type') == 'object' and isinstance(value, dict):
        for key, child in schema.get('properties', {}).items():
            found += unknown_paths(child, value.get(key), path + '.' + key)
    if schema.get('type') == 'array' and isinstance(value, list):
        for index, item in enumerate(value):
            found += unknown_paths(schema['items'], item, path + f'[{index}]')
    return found


def compare(root, *, expected_schema_sha=SCHEMA_SHA):
    root = Path(root)
    directory = root / 'reuse_first_20261115/run01/benchmark20'
    # The worker holds an exclusive lock through its final SHA-manifest write.
    with (directory / 'WORKER.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return _compare_completed(directory, expected_schema_sha)


def _compare_completed(directory, expected_schema_sha):
    state = read(directory / 'RUN_STATUS_PUBLIC.json')
    require(state.get('status') == 'finite_benchmark_completed' and
            state.get('completed') == state.get('selected') == 20,
            'finite20_completion_required')
    require(state.get('original_ledgers_unchanged') is True, 'original_ledgers_not_verified_unchanged')
    expected_results = [directory / 'results' / f'case{i:04d}' / 'RESULT_PUBLIC.json' for i in range(20)]
    require(set((directory / 'results').glob('case*/RESULT_PUBLIC.json')) == set(expected_results),
            'exact20_result_receipts_required')
    sums = read(directory / 'SHA256SUMS_PRIVATE.json')
    preparation = read(directory / 'PREPARATION_PUBLIC.json')
    source_hashes = {}

    def pin(path, expected=None):
        path = Path(path)
        relative = str(path.relative_to(directory))
        digest = sha(path)
        require(digest == (sums.get(relative) if expected is None else expected), 'comparison_input_SHA_mismatch')
        source_hashes[relative] = digest
        return path

    pin(directory / 'RUN_STATUS_PUBLIC.json')
    pin(directory / 'PREPARATION_PUBLIC.json')
    for name in ('SCHEMA.json', 'SELECTION_PRIVATE.json', 'REFERENCES_PRIVATE.jsonl'):
        expected = preparation['output_sha256'][name]
        pin(directory / name, expected)
        require(sums.get(name) == expected, 'worker_preparation_pin_disagreement')
    require(source_hashes['SCHEMA.json'] == expected_schema_sha, 'frozen_schema_pin_mismatch')
    pin(directory / 'EXCLUSIONS_PRIVATE.json')
    schema = read(directory / 'SCHEMA.json')
    required = schema['required']
    business = [key for key in required if key not in IDENTITY]
    bindings = read(directory / 'SELECTION_PRIVATE.json')
    require(len(bindings) == 20 and len({b['audit_id'] for b in bindings}) == 20 and
            len({b['context_sha256'] for b in bindings}) == 20, 'selection_binding_not_unique20')
    protected = set(read(directory / 'EXCLUSIONS_PRIVATE.json')['tasks'])
    results = [read(pin(path)) for path in expected_results]
    status_counts = dict(collections.Counter(row.get('status', 'missing_status') for row in results))
    passed_count = status_counts.get('frozen_validator_pass_candidate_only', 0)
    require(state.get('engineering_pass') == passed_count, 'engineering_count_mismatch')
    refs = []
    # The preparation receipt pins row order. Skip protected lines as bytes;
    # neither their reference JSON nor any protected response body is parsed.
    with (directory / 'REFERENCES_PRIVATE.jsonl').open('rb') as stream:
        for index, raw in enumerate(stream):
            require(index < 20, 'reference_row_count_mismatch')
            binding, result = bindings[index], results[index]
            blocked = (binding['task'] in protected or 'quarantin' in result.get('status', '') or
                       'batch035' in binding['task'].lower() or
                       '01a17beb-973b-74e2-adbb-20f8d004b1fc' in binding['task'])
            refs.append(None if blocked else json.loads(raw))
    require(len(refs) == 20, 'reference_row_count_mismatch')
    categories = {f'{group}.{key}': {'paired': 0, 'exact': 0, 'confusion': collections.Counter()}
                  for group in OUTCOMES for key in schema['properties'][group]['required']}
    for key in ('document_status', 'technology_inventory_status'):
        categories[key] = {'paired': 0, 'exact': 0, 'confusion': collections.Counter()}
    arrays = {key: {'paired': 0, 'full_item_multiset_exact_records': 0,
                    'without_quotes_multiset_exact_records': 0, 'reference_items': 0,
                    'candidate_items': 0, 'full_exact_matched_items': 0,
                    'without_quotes_exact_matched_items': 0} for key in ARRAYS}
    coverage = {'paired_review_records': 0, 'reference_records_with_enum_unknown': 0,
                'candidate_records_with_enum_unknown': 0, 'reference_enum_unknown_count': 0,
                'candidate_enum_unknown_count': 0, 'candidate_records_with_unresolved_notes': 0,
                'protected_records_skipped_without_reference_parse': 0,
                'nonpass_records_excluded_from_content_comparison': 0}
    full_exact, no_quotes_exact, private_rows = 0, 0, []
    for index, (binding, result, reference) in enumerate(zip(bindings, results, refs)):
        detail = {'ordinal': index, 'audit_id': binding['audit_id'], 'task': binding['task'],
                  'engineering_status': result.get('status')}
        if reference is None:
            coverage['protected_records_skipped_without_reference_parse'] += 1
            detail['comparison'] = 'protected_not_parsed'
            private_rows.append(detail)
            continue
        require(reference['audit_id'] == binding['audit_id'], 'reference_order_binding_mismatch')
        ref = reference['review']
        require(all(k in ref for k in required) and all(ref[k] == binding[k] for k in IDENTITY),
                'reference_identity_or_schema_contract_mismatch')
        if result.get('status') != 'frozen_validator_pass_candidate_only':
            coverage['nonpass_records_excluded_from_content_comparison'] += 1
            detail['comparison'] = 'no_validated_candidate_not_counted_as_agreement'
            private_rows.append(detail)
            continue
        vp = pin(directory / 'results' / f'case{index:04d}' / 'VALIDATED_PRIVATE.jsonl')
        rows = [json.loads(line) for line in vp.read_text().splitlines() if line.strip()]
        require(len(rows) == 1 and all(k in rows[0] for k in required), 'validated_review_schema_contract_failure')
        candidate = {k: rows[0][k] for k in required}
        require(all(candidate[k] == binding[k] for k in IDENTITY), 'candidate_identity_mismatch')
        coverage['paired_review_records'] += 1
        mismatch = []
        for name, counts in categories.items():
            if '.' in name:
                group, key = name.split('.')
                rv, cv = ref[group][key], candidate[group][key]
            else:
                rv, cv = ref[name], candidate[name]
            counts['paired'] += 1
            counts['exact'] += rv == cv
            counts['confusion'][(rv, cv)] += 1
            if rv != cv:
                mismatch.append(name)
        for name, counts in arrays.items():
            original = array_exact(ref[name], candidate[name])
            diagnostic = array_exact(ref[name], candidate[name], strip_quotes=True)
            counts['paired'] += 1
            counts['full_item_multiset_exact_records'] += original['array_multiset_exact']
            counts['without_quotes_multiset_exact_records'] += diagnostic['array_multiset_exact']
            counts['reference_items'] += original['reference_items']
            counts['candidate_items'] += original['candidate_items']
            counts['full_exact_matched_items'] += original['matched_exact_items']
            counts['without_quotes_exact_matched_items'] += diagnostic['matched_exact_items']
        rb, cb = ({k: value[k] for k in business} for value in (ref, candidate))
        same = canonical(rb) == canonical(cb)
        diagnostic_same = canonical(rb, strip_quotes=True) == canonical(cb, strip_quotes=True)
        full_exact += same
        no_quotes_exact += diagnostic_same
        ru, cu = unknown_paths(schema, ref), unknown_paths(schema, candidate)
        coverage['reference_records_with_enum_unknown'] += bool(ru)
        coverage['candidate_records_with_enum_unknown'] += bool(cu)
        coverage['reference_enum_unknown_count'] += len(ru)
        coverage['candidate_enum_unknown_count'] += len(cu)
        coverage['candidate_records_with_unresolved_notes'] += bool(candidate['unresolved_notes'])
        detail.update(comparison='paired_validated_reviews', categorical_mismatch_fields=mismatch,
                      full_business_structure_exact=same, without_quotes_structure_exact=diagnostic_same,
                      candidate_unknown_paths=cu)
        private_rows.append(detail)
    for counts in categories.values():
        counts['exact_agreement_fraction_among_paired'] = counts['exact'] / counts['paired'] if counts['paired'] else None
        counts['confusion'] = [{'reference': a, 'candidate': b, 'n': n}
                               for (a, b), n in sorted(counts['confusion'].items())]
    paired = coverage['paired_review_records']
    report = {
        'status': 'finite20_relative_exact_comparison_complete_not_quality_certification',
        'selected_records': 20, 'engineering_result_counts': status_counts,
        'engineering_pass_records': passed_count, 'engineering_pass_fraction_selected20': passed_count / 20,
        'comparison_coverage': coverage, 'categorical_exact_agreement': categories,
        'relation_array_exact_diagnostics': arrays,
        'full_business_structure_exact_records_among_paired': full_exact,
        'full_business_structure_disagreement_records_among_paired': paired - full_exact,
        'full_business_without_quotes_exact_records_among_paired': no_quotes_exact,
        'missing_unusable_or_protected_not_counted_as_exact': 20 - paired,
        'source_sha256': source_hashes,
        'comparison_rules': {'identity_fields_excluded_after_exact_binding_check': sorted(IDENTITY),
                             'full_structure_keeps_quotes_and_array_order': True,
                             'relation_arrays_top_level_order_ignored_duplicate_counts_kept': True,
                             'nested_branch_order_and_group_branch_identifiers_not_normalized': True,
                             'quote_omission_only_auxiliary_diagnostic_not_evidence_validation': True,
                             'free_text_not_semantically_judged_or_normalized': True,
                             'objects_years_strength_conditions_alternative_relations_all_retained': True},
        'limitations': [
            'Reference is prior Kimi saved-unverified output, not human gold or independent ground truth.',
            'First20 known-full/no-prior-unknown eligible records are selected, not a random population sample.',
            'Agreement with this reference is not correctness, semantic accuracy, precision, recall, F1 or a production quality pass.',
            'Only engineering-pass nonprotected candidates enter content comparisons; coverage and selected20 engineering denominator remain explicit.',
            'Exact matching may disagree on semantically equivalent wording/group IDs or agree on shared errors.',
            'Removing quotes is auxiliary only and cannot establish valid evidence or valid complete relations.',
        ],
        'precision_recall_F1_computed': False, 'population_accuracy_claimed': False,
        'new_model_calls': 0, 'new_production_accepted': 0, 'automatic_promotion': False,
        'historical_results_modified': False,
    }
    require(all(sha(directory / relative) == digest for relative, digest in source_hashes.items()),
            'source_changed_during_comparison')
    out = directory / 'comparison_v1'
    if out.exists():
        require((out / 'COMPARISON_PUBLIC.json').is_file() and
                read(out / 'COMPARISON_PUBLIC.json') == report, 'existing_comparison_conflict_preserved')
        saved = read(out / 'SHA256SUMS_PUBLIC.json')
        require(all(sha(out / name) == digest for name, digest in saved.items()), 'existing_comparison_SHA_mismatch')
        return report
    out.mkdir(mode=0o700)
    data = {'COMPARISON_PUBLIC.json': (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode(),
            'DISAGREEMENTS_PRIVATE.jsonl': ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in private_rows).encode()}
    for name, body in data.items():
        with (out / name).open('xb') as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
    with (out / 'SHA256SUMS_PUBLIC.json').open('x') as f:
        json.dump({name: sha(out / name) for name in data}, f, indent=2)
        f.write('\n')
    return report


if __name__ == '__main__':
    os.umask(0o077)
    try:
        summary = compare(Path.home() / 'migration')
        print(json.dumps({k: summary[k] for k in ('status', 'selected_records', 'engineering_pass_records',
                                                'comparison_coverage', 'new_production_accepted')}))
    except Exception as error:
        print(json.dumps({'status': 'comparison_failed_preserve_inputs', 'error_type': type(error).__name__,
                          'reason': str(error) if isinstance(error, RuntimeError) else 'details_not_logged'}))
        raise SystemExit(2)
