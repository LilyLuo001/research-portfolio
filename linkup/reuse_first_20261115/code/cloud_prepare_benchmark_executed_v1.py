"""Prepare one immutable 20-row independent model benchmark on Azure.

No inference, source resampling, production promotion, old-label update or
protected-source parsing. Run on the existing VM as linkup. The only real
source bodies parsed are the selected ordinary candidates, after all status
and unknown exclusions. Reference predictions are a separate private file.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path

POLICY_SHA = '7a3416c5cd8e515526f59c1f159e914b6d691f191aa11a82a2556637e4a09df7'
PINS = {
    'code/validate_reviews.py': 'f7737143004374f9391a16ad2d1bab2fa47950c589232510045d1eee93bc2c20',
    'astra/extraction/FORMAL800_REVIEW_SCHEMA.json': 'fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e',
    'astra/extraction/REVIEW_INSTRUCTIONS.md': 'f13e1c431b4018fb7d1e2f1dc985dece69f092a8713c7ef673497a0fbd728d26',
}
FORM_SHA = '95e7c79dc5edff1bb8d3b37907b1db17430f37c61090083748d8bf7fd5bd3c25'
PROTECTED_FIRST = 'batch052/packet_0095/1'
FORBIDDEN_MARKERS = ('batch035', '01a17beb-973b-74e2-adbb-20f8d004b1fc')
SELECT_N = 20


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(p):
    return json.loads(Path(p).read_text())


def jsonl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def enum_unknown(schema, value):
    """Only schema enum states count, never words inside quotes/free text."""
    if 'enum' in schema and value in ('unknown', 'unresolved'):
        return True
    if schema.get('type') == 'object' and isinstance(value, dict):
        return any(enum_unknown(s, value.get(k)) for k, s in schema['properties'].items())
    if schema.get('type') == 'array' and isinstance(value, list):
        return any(enum_unknown(schema['items'], x) for x in value)
    return False


def prepare(root, *, expected_policy_sha=POLICY_SHA, expected_pins=None,
            expected_form_sha=FORM_SHA):
    os.umask(0o077)
    root = Path(root)
    expected_pins = PINS if expected_pins is None else expected_pins
    base = root / 'opencode_kimi_20261115/run01/bulk_1309_20261115'
    results = base.parent / 'results/bulk1309'
    audit = base / 'human_audit'
    out = root / 'reuse_first_20261115/run01/benchmark20'
    receipt_path = out / 'PREPARATION_PUBLIC.json'
    if receipt_path.exists():
        receipt = read(receipt_path)
        for path, digest in receipt['source_sha256'].items():
            require(sha(path) == digest, 'existing_benchmark_source_changed')
        for name, digest in receipt['output_sha256'].items():
            require(sha(out / name) == digest, 'existing_benchmark_output_changed')
        return receipt
    require(not out.exists(), 'partial_benchmark_preserved_do_not_overwrite')
    watched = {}

    def watch(p):
        p = Path(p)
        require(p.is_file(), 'required_source_missing')
        digest = sha(p)
        if str(p) in watched:
            require(watched[str(p)] == digest, 'source_changed_during_preparation')
        watched[str(p)] = digest
        return digest

    policy_path = root / 'research_policy_20261115_ai_review/POLICY_V4_ECONOMICS_FIRST_PUBLIC.json'
    require(watch(policy_path) == expected_policy_sha, 'policy_pin_mismatch')
    policy = read(policy_path)
    require(policy.get('human_review_required') is False and
            policy.get('frozen_business_schema_and_evidence_rules_preserved') is True and
            policy.get('execution', {}).get('no_protected_content_reroute_or_reinference') is True,
            'policy_boundary_not_satisfied')
    final_path, ledger_path = base / 'FINAL_PUBLIC.json', base / 'CANDIDATE_STATE_PRIVATE.json'
    claim_path = base / 'CLAIM_PRIVATE.json'
    ids_path = root / 'AZURE_RESEARCH_IDENTITIES_PRIVATE.json'
    state_path = root / 'AZURE_RESEARCH_STATE.json'
    old_accepted = root / 'astra/extraction/STATE_PRIVATE.json'
    for p in (final_path, ledger_path, claim_path, ids_path, state_path, old_accepted):
        watch(p)
    final, ledger, claim, state = read(final_path), read(ledger_path), read(claim_path), read(state_path)
    require(final['handled'] == len(ledger['handled']) == 1309, 'finite_source_not_complete')
    require(final['frozen_pass_candidates'] == len(ledger['engineering_candidates']), 'candidate_count_mismatch')
    require(not ledger.get('production_promoted') and not ledger.get('semantic_quality_certified'),
            'source_no_longer_unpromoted_candidates')
    require(watched[str(old_accepted)] == claim['old_accepted_sha256'], 'old_accepted_changed')
    for rel, digest in expected_pins.items():
        require(claim['pins'].get(rel) == digest and watch(root / rel) == digest, 'frozen_pin_mismatch')
    schema = read(root / 'astra/extraction/FORMAL800_REVIEW_SCHEMA.json')
    require(watched[str(ids_path)] == state['private_record_index']['sha256'], 'identity_index_pin_mismatch')
    identities = read(ids_path)['rows']
    bytask = {x['task']: x for x in identities}
    require(len(bytask) == len(identities), 'duplicate_task_identity')
    protected = {PROTECTED_FIRST}
    for task, value in ledger['exceptions'].items():
        if value.get('disposition') == 'quarantined' or any(x in value.get('status', '') for x in ('quarantin', 'content_filter')):
            protected.add(task)
    events_path = base / 'QUARANTINE_EVENTS_PRIVATE.json'
    if events_path.exists():
        watch(events_path)
        events = read(events_path)
        for e in events.get('events', []):
            if e.get('disposition') == 'quarantined' or e.get('retry_forbidden'):
                protected.add(e['task'])
    for e in state.get('quarantine_register', []):
        if e.get('task'):
            protected.add(e['task'])
    protected_hashes = {bytask[t]['context_sha256'] for t in protected if t in bytask}
    accepted = set(claim.get('known_completed_tasks', [])) | {
        x['task'] for x in identities if x.get('execution_state') in ('accepted', 'reviewed_unknown', 'quarantined')}
    accepted |= set(state.get('deduplication', {}).get('known_accepted_duplicates_in_checked_parent_scopes', []))
    accepted_hashes = {bytask[t]['context_sha256'] for t in accepted if t in bytask}
    form_path, key_path = audit / 'BLIND_HUMAN_REVIEW_FORM_PRIVATE.jsonl', audit / 'SEALED_MATCH_KEY_PRIVATE.jsonl'
    require(watch(form_path) == expected_form_sha == final['audit_file_sha256']['BLIND_HUMAN_REVIEW_FORM_PRIVATE.jsonl'], 'audit_form_changed')
    require(watch(key_path) == final['audit_file_sha256']['SEALED_MATCH_KEY_PRIVATE.jsonl'], 'audit_match_key_changed')
    keys = jsonl(key_path)
    require(len(keys) == 200 and [x['audit_id'] for x in keys] == [f'BLIND-{i:04d}' for i in range(1, 201)], 'frozen_audit_order_changed')
    require(len({x['task'] for x in keys}) == 200, 'duplicate_audit_task')
    candidates, skips, reference_cache = [], collections.Counter(), {}
    for item in keys:
        task, h = item['task'], item['context_sha256']
        if task in protected or h in protected_hashes or any(v in task for v in FORBIDDEN_MARKERS):
            skips['protected'] += 1
            continue  # Never open that candidate's review/input files.
        if task in accepted or h in accepted_hashes:
            skips['already_accepted_or_reviewed_unknown'] += 1
            continue
        if task not in ledger['engineering_candidates'] or ledger['handled'].get(task, {}).get('status') != 'frozen_validator_pass_candidate_only':
            skips['prior_exception_or_non_candidate'] += 1
            continue
        candidate = ledger['engineering_candidates'][task]
        require(task in bytask and bytask[task]['context_sha256'] == h == candidate['context_sha256'], 'candidate_identity_mismatch')
        require(candidate['record_id'] == item['record_id'] == bytask[task]['record_id'], 'candidate_record_id_mismatch')
        require(candidate.get('semantic_quality') == 'not_certified' and candidate.get('validation') == 'frozen_validator_pass', 'not_saved_unverified_candidate')
        vp = Path(candidate['path']).resolve()
        require(vp.name == 'CLOUD_VALIDATED_PRIVATE.jsonl' and results.resolve() in vp.parents, 'candidate_path_outside_source_run')
        require(watch(vp) == candidate['validated_sha256'], 'candidate_validated_hash_mismatch')
        validated = jsonl(vp)
        require(len(validated) == 1, 'candidate_row_count_mismatch')
        review = {k: validated[0][k] for k in schema['required']}
        require(review['record_id'] == item['record_id'] and review['context_sha256'] == h, 'reference_binding_mismatch')
        if review.get('document_status') != 'reviewed_full':
            skips['prior_partial_or_unresolved'] += 1
            continue
        if enum_unknown(schema, review) or review.get('unresolved_notes'):
            skips['prior_unknown_or_unresolved'] += 1
            continue
        candidates.append({**item, 'source_input': str(vp.parent / 'INPUT_PRIVATE.jsonl'), 'validation_file': str(vp)})
        reference_cache[item['audit_id']] = review
    require(len(candidates) >= SELECT_N, 'fewer_than20_eligible_no_resampling')
    selected = candidates[:SELECT_N]
    # Read only selected ordinary source rows; other lines are skipped as bytes.
    want = {x['audit_id']: x for x in selected}
    forms = {}
    line_count = 0
    with form_path.open('rb') as stream:
        for line_count, raw in enumerate(stream, 1):
            aid = f'BLIND-{line_count:04d}'
            if aid not in want:
                continue
            f = json.loads(raw)
            require(f['audit_id'] == aid and f['gold_review'] is None, 'source_form_identity_or_gold_changed')
            require(hashlib.sha256(f['full_document'].encode()).hexdigest() == want[aid]['context_sha256'], 'audit_document_hash_mismatch')
            forms[aid] = f
    require(line_count == 200 and len(forms) == SELECT_N, 'source_form_row_count_mismatch')
    inputs, references, bindings = [], [], []
    for item in selected:
        aid = item['audit_id']
        ip = Path(item['source_input'])
        watch(ip)
        hash_path = ip.parent.parent / 'SHA256SUMS.json'
        watch(hash_path)
        manifest = read(hash_path)
        require(watched[str(ip)] == manifest[str(ip.relative_to(hash_path.parent))], 'source_input_manifest_hash_mismatch')
        original = jsonl(ip)
        require(len(original) == 1, 'source_input_row_count_mismatch')
        original = original[0]
        require(original['record_id'] == item['record_id'] and original['context_sha256'] == item['context_sha256'] and original['full_document'] == forms[aid]['full_document'], 'source_input_binding_mismatch')
        row = {k: original[k] for k in ('record_id', 'context_sha256', 'full_document')}
        row['assignment'] = {'packet_id': 'reuse_first_benchmark20', 'reviewer_role': 'blind_audit', 'audit_id': aid,
                             'provenance': 'independent candidate benchmark; not production reread or human gold'}
        inputs.append({'audit_id': aid, 'task': item['task'], 'row': row})
        references.append({'audit_id': aid, 'review': reference_cache[aid]})
        bindings.append({k: item[k] for k in ('audit_id', 'task', 'record_id', 'context_sha256', 'source_input', 'validation_file')})
    require(all(sha(p) == digest for p, digest in watched.items()), 'old_source_changed_during_preparation')
    out.mkdir(parents=True, mode=0o700)
    payloads = {
        'INPUTS_PRIVATE.jsonl': ''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in inputs).encode(),
        'REFERENCES_PRIVATE.jsonl': ''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in references).encode(),
        'SELECTION_PRIVATE.json': (json.dumps(bindings, indent=2)+'\n').encode(),
        'SCHEMA.json': (root / 'astra/extraction/FORMAL800_REVIEW_SCHEMA.json').read_bytes(),
        'INSTRUCTIONS.md': (root / 'astra/extraction/REVIEW_INSTRUCTIONS.md').read_bytes(),
    }
    for name, data in payloads.items():
        with (out / name).open('xb') as f:
            f.write(data)
    after = {p: sha(p) for p in watched}
    require(after == watched, 'old_source_changed_before_commit')
    report = {
        'status': 'benchmark20_prepared_not_submitted',
        'prepared_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'output_directory': str(out), 'selected_n': SELECT_N,
        'input_sha256': sha(out/'INPUTS_PRIVATE.jsonl'),
        'schema_sha256': sha(out/'SCHEMA.json'), 'instructions_sha256': sha(out/'INSTRUCTIONS.md'),
        'input_path': str(out/'INPUTS_PRIVATE.jsonl'), 'references_path': str(out/'REFERENCES_PRIVATE.jsonl'),
        'source_audit_n': 200, 'eligible_existing_candidates': len(candidates),
        'selection_rule': 'first20_in_original_BLIND_order_after_frozen_state_exclusions; never replace based on new model results',
        'selected_audit_ids': [x['audit_id'] for x in selected], 'exclusions': dict(skips),
        'benchmark_scope': 'compatibility of a fixed known fully reviewed saved-unverified subset; not population accuracy',
        'comparison_thresholds': {'relative_reference_precision': 0.90, 'relative_reference_recall': 0.80, 'relative_reference_macro_f1': 0.85,
                                  'interpretation': 'candidate compatibility comparison only; small support is insufficient, not a population certification'},
        'pins': expected_pins, 'source_sha256': watched, 'source_sha256_after': after,
        'output_sha256': {name: sha(out/name) for name in payloads},
        'old_ledger_before_sha256': watched[str(ledger_path)], 'old_ledger_after_sha256': after[str(ledger_path)],
        'old_files_unchanged': True, 'selected_source_rows_parsed': SELECT_N,
        'protected_source_rows_parsed': 0, 'blind_inputs_contain_reference_answers': False,
        'model_calls': 0, 'production_increment': 0, 'production_promoted': 0,
        'human_certification': False, 'policy_sha256': expected_policy_sha,
        'full_scope_delivery_goal_unchanged': True,
    }
    with receipt_path.open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return report


if __name__ == '__main__':
    try:
        r = prepare(Path('/home/linkup/migration'))
        print(json.dumps({k:r[k] for k in ('status','output_directory','selected_n','input_sha256','schema_sha256','instructions_sha256','source_audit_n','eligible_existing_candidates','exclusions','old_files_unchanged','model_calls','production_increment')}))
    except Exception as error:
        # Fixed reason strings only; never expose source content in traceback.
        print(json.dumps({'status':'benchmark_preparation_failed_preserve_files','error_type':type(error).__name__,
                          'reason':str(error) if isinstance(error,RuntimeError) else 'source_or_execution_error_details_not_printed',
                          'model_calls':0,'production_increment':0}))
        raise SystemExit(1)
