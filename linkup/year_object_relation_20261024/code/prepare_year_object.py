#!/usr/bin/env python3
"""Scheduled, create-only year-mention inputs and accepted same-item binding.

The frozen numeric regex/clauses are reused unchanged. Candidate generation has
no teacher argument. This script neither trains nor creates reference negatives.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

SPLITS = ('train', 'final_previously_exposed', 'previous_holdout_reserved_not_final')
HOLDOUT_SHA = '5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1'
CORE = ('general_work', 'occupation_task', 'industry_domain', 'tool_specific')
RADIUS = 192
ANALYSIS_FRAME_SHA = '70ab7ed24697cf456e738497de4eec02531205294a626a0dab66bb779a0db1a6'
GA = 'genai_use_with_or_without_software'
GB = 'traditional_software_use_no_ai'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rows(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write(path, value, lines=False):
    with open(path, 'x', encoding='utf-8') as f:
        os.chmod(path, 0o600)
        if lines:
            for r in value:
                f.write(json.dumps(r, sort_keys=True, ensure_ascii=False) + '\n')
        else:
            json.dump(value, f, sort_keys=True, ensure_ascii=False, indent=2)
            f.write('\n')


def checked(x):
    if sha(x['path']) != x['sha256']:
        raise RuntimeError('frozen input digest mismatch')
    return x['path']


def membership_sha(values):
    return hashlib.sha256(('\n'.join(sorted(set(values))) + '\n').encode()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def context_inventory(inputs, analysis_frame):
    """Context metadata only: never consulted by candidate generation/binding.

    Multiple advertisements sharing complete text count as one context. No
    advertisement-weighted group proportions or majority choice are introduced.
    """
    grouped = collections.defaultdict(lambda: dict(groups=set(), years=set(), objects=set(), ads=0))
    if analysis_frame:
        if sha(analysis_frame) != ANALYSIS_FRAME_SHA:
            raise RuntimeError('approved analysis-frame digest mismatch')
        import pyarrow.parquet as pq
        cols = ['normalized_context_sha256', 'technology_group',
                'status_experience_object', 'status_experience_literal_years']
        table = pq.read_table(analysis_frame, columns=cols)
        for r in table.to_pylist():
            g = grouped[r['normalized_context_sha256']]
            g['groups'].add(r['technology_group'])
            g['years'].add(r['status_experience_literal_years'])
            g['objects'].add(r['status_experience_object'])
            g['ads'] += 1
        provenance = dict(source='approved_analysis_frame_four_metadata_columns_only',
            sha256=ANALYSIS_FRAME_SHA, ad_rows=table.num_rows)
    else:
        ledger_path = checked(inputs['ledger'])
        count = 0
        for r in rows(ledger_path):
            count += 1
            family = r['field_family']
            if family not in ('experience_object', 'experience_literal_years'):
                continue
            g = grouped[r['normalized_context_sha256']]
            g['objects' if family == 'experience_object' else 'years'].add(r['status'])
        if count != 70000:
            raise RuntimeError('frozen accepted-family inventory must preserve all70000 masks')
        provenance = dict(source='checked_frozen_ledger_all70000_masks', sha256=inputs['ledger']['sha256'], family_rows=count)
    metadata = {}
    for c, g in grouped.items():
        raw_groups = g['groups']
        conflict = len(raw_groups) > 1
        raw = next(iter(raw_groups)) if len(raw_groups) == 1 else None
        if raw == GA:
            reference_group = 'GA'
        elif raw == GB:
            reference_group = 'GB'
        elif raw is None or raw in ('unknown', 'unresolved', 'uncertain_technology', 'unknown_reference_membership'):
            reference_group = 'unknown'
        else:
            reference_group = 'other'
        y = next(iter(g['years'])) if len(g['years']) == 1 else 'unknown_or_conflicting'
        o = next(iter(g['objects'])) if len(g['objects']) == 1 else 'unknown_or_conflicting'
        metadata[c] = dict(reference_group=reference_group, reference_group_conflict=conflict,
            year_family_status=y, object_family_status=o,
            inventory_eligible=y in ('known', 'not_applicable') and o in ('known', 'not_applicable'),
            analysis_frame_ad_rows=g['ads'] if analysis_frame else None,
            metadata_granularity='one_normalized_complete_context_unweighted')
    return metadata, provenance


def candidates(rule, context, text, split):
    """Production-only fixed numeric spans and fixed windows, before teacher IO."""
    result = rule.extract(text)
    if result.get('status') != 'processed':
        return [], 'frozen_engine_invalid_context'
    if result.get('normalized_text') != text:
        return [], 'frozen_normalization_not_idempotent'
    clauses = list(rule.clauses(text))
    for clause, start, section in clauses:
        if text[start:start + len(clause)] != clause:
            raise RuntimeError('frozen clause coordinate mismatch')
    seen, out = set(), []
    # The unchanged frozen regex may include whitespace across a line boundary.
    # Enumerate once globally rather than erase such spans at clause boundaries.
    for m in rule.YEARS.finditer(text):
        left, right = m.start(), m.end()
        key = (left, right)
        if key in seen:
            raise RuntimeError('duplicate numeric candidate coordinates')
        seen.add(key)
        enclosing = [(s, b, sec) for s, b, sec in clauses if b <= left and right <= b + len(s)]
        if len(enclosing) > 1:
            raise RuntimeError('multiple frozen clauses enclose a numeric span')
        clause, start, section = enclosing[0] if enclosing else (None, None, None)
        low, high = max(0, left - RADIUS), min(len(text), right + RADIUS)
        duration = rule.duration(m)
        old = [dict(e) for e in result['evidence']
               if e.get('kind') == 'experience' and e['start'] <= m.start('lo') and m.end('unit') <= e['end']]
        cid = hashlib.sha256((context + '|%d|%d' % key).encode()).hexdigest()
        out.append(dict(candidate_id=cid, context_sha256=context, split=split,
            entity_start=left, entity_end=right, term=text[left:right],
            numeric_value_start=m.start('lo'), numeric_unit_end=m.end('unit'),
            clause_start=start, clause_end=start + len(clause) if clause is not None else None, section=section,
            clause_state='unique_frozen_clause' if enclosing else 'cross_clause_frozen_numeric_span',
            window_start=low, window_end=high,
            model_input=text[low:left] + '[YEAR]' + text[left:right] + '[/YEAR]' + text[right:high],
            frozen_duration=duration, frozen_experience_evidence=old,
            primary_old_experience_candidate=bool(old),
            frozen_technology_flags={k: v for k, v in result.get('flags', {}).items() if k.startswith('tech_')},
            frozen_numeric_groups=m.groupdict(),
            candidate_source='unchanged_frozen_year_regex_global_with_frozen_clause_evidence'))
    if len(out) != len(seen):
        raise RuntimeError('frozen numeric occurrence conservation failed')
    return out, 'processed'


def equal(a, b):
    return a is None and b is None or (isinstance(a, (int, float)) and not isinstance(a, bool)
        and isinstance(b, (int, float)) and not isinstance(b, bool)
        and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9))


def numeric_match(candidate, labels):
    """Conserve all stated scalar/range values in years, including month units.

    Bare scalar regex syntax has no semantic min/max/exact assertion. Original
    accepted relation may supply that assertion, while its number must match.
    Explicit prefix/range contradictions are preserved as unbindable.
    """
    d, relation = candidate['frozen_duration'], labels.get('years_relation')
    low, high = labels.get('years_min'), labels.get('years_max')
    if relation == 'not_stated' or low is None and high is None:
        return False
    kind = d['kind']
    if kind == 'range':
        return relation == 'range' and equal(d['lower_years'], low) and equal(d['upper_years'], high)
    if kind == 'maximum':
        return relation == 'at_most' and low is None and equal(d['upper_years'], high)
    if kind == 'minimum':
        return relation == 'at_least' and high is None and equal(d['lower_years'], low)
    n = d['lower_years']
    if kind == 'exact':
        return relation == 'exact' and equal(low, n) and equal(high, n)
    return ((relation == 'at_least' and high is None and equal(low, n))
            or (relation == 'at_most' and low is None and equal(high, n))
            or (relation == 'exact' and equal(low, n) and equal(high, n)))


def identity(row):
    return tuple(row[k] for k in ('context_sha256', 'source_sha256', 'source_record_id', 'original_item_path'))


def bind(by_context, original, partition, context_states=None):
    """Match numeric evidence in both directions without old-object filtering."""
    object_rows = collections.defaultdict(list)
    for r in original:
        if r['field_family'] == 'experience_object':
            object_rows[identity(r)].append(r)
    refs, links = [], collections.defaultdict(list)
    context_states = context_states or {}
    for index, r in enumerate(original):
        if r['field_family'] != 'experience_literal_years':
            continue
        c, labels = r['context_sha256'], r['labels']
        if c not in by_context or r['split'] != partition(c):
            raise RuntimeError('reference context/split mismatch')
        evidence = r.get('evidence', [])
        spans = [s for e in evidence for s in e.get('occurrences', [])]
        repeated = any(len(e.get('occurrences', [])) > 1 for e in evidence)
        overlapping = [x for x in by_context[c] if any(
            s['start'] < x['entity_end'] and x['entity_start'] < s['end'] for s in spans)]
        # Exact frozen subgroup coordinates allow a quote that omits a prefix
        # ('at least') while still requiring every number, range and unit.
        contained = [x for x in overlapping if any(
            s['start'] <= x['numeric_value_start'] and x['numeric_unit_end'] <= s['end'] for s in spans)]
        matched = [x for x in contained if numeric_match(x, labels)]
        accepted = object_rows[identity(r)]
        mask_ok = len(accepted) == 1 and accepted[0]['labels']['object'] == labels['object']
        context_state = context_states.get(c, 'processed')
        if labels.get('years_relation') == 'not_stated':
            state = 'original_no_literal_year_not_a_negative'
        elif context_state != 'processed':
            state = 'candidate_generation_context_unavailable'
        elif not evidence or not spans:
            state = 'original_numeric_evidence_unavailable'
        elif not overlapping:
            state = 'true_frozen_candidate_absence_in_reference_evidence'
        elif not contained:
            state = 'nonliteral_reference_numeric_or_unit_span_not_contained'
        elif not matched:
            state = 'nonliteral_or_numeric_binding_mismatch'
        elif repeated:
            state = 'ambiguous_repeated_reference_quote'
        elif len(matched) != 1:
            state = 'ambiguous_multiple_numeric_matches'
        elif not mask_ok:
            state = 'accepted_object_family_binding_unavailable_or_conflicting'
        else:
            state = 'matched_unique'
        rid = hashlib.sha256((c + '|' + str(index) + '|' + r['original_item_path']).encode()).hexdigest()
        ref = dict(reference_id=rid, context_sha256=c, split=r['split'], labels=labels,
            source_sha256=r['source_sha256'], source_record_id=r['source_record_id'],
            original_item_path=r['original_item_path'], original_item_audit_only=r.get('original_item_audit_only'),
            evidence=evidence, accepted_family_masks=dict(experience_literal_years=True,
                experience_object_same_original_item=mask_ok),
            bound_original_item_identity=list(identity(r)),
            candidate_generation_context_state=context_state,
            accepted_same_item_experience_tuple=r.get('accepted_same_item_experience_tuple'),
            contained_candidate_ids=[x['candidate_id'] for x in contained],
            overlapping_candidate_ids=[x['candidate_id'] for x in overlapping],
            candidate_ids=[x['candidate_id'] for x in matched], localization_state=state)
        refs.append(ref)
        for x in matched:
            links[x['candidate_id']].append(ref)
    associated, fit, evaluation = [], [], []
    classes = sorted(set(CORE) | {r['labels']['object'] for r in refs})
    for xs in by_context.values():
        for x in xs:
            linked = links[x['candidate_id']]
            objects = {r['labels']['object'] for r in linked}
            if not linked:
                state = 'unlabeled_candidate_no_negative'
            elif len(objects) > 1:
                state = 'conflicting_original_objects'
            elif len(linked) > 1:
                state = 'ambiguous_multiple_original_items'
            elif linked[0]['localization_state'] != 'matched_unique':
                state = 'ambiguous_or_unaccepted_original_binding'
            elif next(iter(objects)) in ('unknown', 'unresolved'):
                state = 'unknown_original_object_no_negative'
            else:
                state = 'compatible_unique_reference'
            row = dict(candidate_id=x['candidate_id'], context_sha256=x['context_sha256'], split=x['split'],
                supervision_state=state, reference_ids=[r['reference_id'] for r in linked])
            if state == 'compatible_unique_reference':
                ref = linked[0]
                label = ref['labels']['object']
                row.update(label=label, label_id=classes.index(label), bound_original_item=ref)
                value = dict(x, **row)
                (fit if x['split'] == 'train' else evaluation).append(value)
            associated.append(row)
    return refs, associated, fit, evaluation, classes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ('recovered', 'input-manifest', 'frozen-rule-dir', 'expected-rule-sha256', 'expected-legacy-sha256', 'output'):
        p.add_argument('--' + option, required=True)
    p.add_argument('--analysis-frame', help='Optional root-approved metadata-only AD_LEVEL parquet; fixed expected SHA')
    a = p.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('actual scheduled SCNet job required')
    root = Path(a.output)
    if root.exists():
        raise RuntimeError('create-only output directory already exists')
    frozen = Path(a.frozen_rule_dir)
    if sha(frozen / 'rule_engine.py') != a.expected_rule_sha256 or sha(frozen / 'legacy_v5_frozen.py') != a.expected_legacy_sha256:
        raise RuntimeError('approved frozen engine hash mismatch')
    sys.path.insert(0, str(frozen))
    import rule_engine as rule
    if rule.VERSION != 'rulefirst-20261008-v1.2':
        raise RuntimeError('wrong frozen engine version')
    manifest = json.loads(Path(a.input_manifest).read_text())
    freeze = json.loads(Path(checked(manifest['freeze'])).read_text())
    inputs = freeze['inputs']
    if inputs['holdout']['sha256'] != HOLDOUT_SHA:
        raise RuntimeError('original final holdout identity changed')
    final = {r['normalized_context_sha256'] for r in rows(checked(inputs['holdout']))}
    if len(final) != 1331:
        raise RuntimeError('original final holdout cardinality changed')
    legacy = load(checked(inputs['legacy']), 'original_holdout_adapter')
    def partition(c):
        return SPLITS[1] if c in final else SPLITS[2] if legacy.is_holdout(c) else SPLITS[0]
    recovered = Path(a.recovered)
    context_path, item_path = recovered / 'CONTEXTS_PRIVATE.jsonl', recovered / 'RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl'
    by_context, context_states, texts = {}, [], {}
    for r in rows(context_path):
        c, text = r['context_sha256'], r['complete_context']
        if c in by_context or hashlib.sha256(text.encode()).hexdigest() != c:
            raise RuntimeError('recovered context identity mismatch')
        xs, state = candidates(rule, c, text, partition(c))
        by_context[c] = xs
        texts[c] = text
        context_states.append(dict(context_sha256=c, split=partition(c), state=state, candidates=len(xs)))
    root.mkdir(parents=True, mode=0o700)
    flat = [x for c in sorted(by_context) for x in by_context[c]]
    write(root / 'CANDIDATES_PRIVATE.jsonl', flat, True)
    inventory, inventory_provenance = context_inventory(inputs, a.analysis_frame)
    for state in context_states:
        state.update(inventory.get(state['context_sha256'], dict(reference_group='unknown',
            reference_group_conflict=False, year_family_status='unavailable', object_family_status='unavailable',
            inventory_eligible=False, analysis_frame_ad_rows=None,
            metadata_granularity='one_normalized_complete_context_unweighted')))
    write(root / 'CONTEXT_STATES_PRIVATE.jsonl', context_states, True)
    # The only teacher read occurs after production candidate persistence.
    original = list(rows(item_path))
    for r in original:
        if r['field_family'] not in ('experience_literal_years', 'experience_object'):
            continue
        c = r['context_sha256']
        if c not in texts or r['split'] != partition(c):
            raise RuntimeError('accepted reference context/split mismatch')
        for ev in r.get('evidence', []):
            for span in ev.get('occurrences', []):
                low, high = span['start'], span['end']
                if not (0 <= low < high <= len(texts[c])) or texts[c][low:high] != ev['quote']:
                    raise RuntimeError('accepted original quote/offset mismatch')
    refs, associated, fit, evaluation, classes = bind(by_context, original, partition,
        {r['context_sha256']: r['state'] for r in context_states})
    write(root / 'REFERENCE_COVERAGE_PRIVATE.jsonl', refs, True)
    write(root / 'CANDIDATE_SUPERVISION_PRIVATE.jsonl', associated, True)
    write(root / 'TRAIN_COMPATIBLE_PRIVATE.jsonl', fit, True)
    write(root / 'EVAL_COMPATIBLE_PRIVATE.jsonl', evaluation, True)
    write(root / 'LABEL_DICTIONARY.json', dict(label_to_id={r: i for i, r in enumerate(classes)}, target='year_mention_to_accepted_experience_object'))
    support = []
    for s in SPLITS:
        for label in classes:
            rs = [r for r in refs if r['split'] == s and r['labels']['object'] == label]
            compatible = [r for r in associated if r['split'] == s and r.get('label') == label]
            compatible_ids = {r['candidate_id'] for r in compatible}
            primary_compatible = [r for r in flat if r['candidate_id'] in compatible_ids and r['primary_old_experience_candidate']]
            numeric = [r for r in rs if r['labels'].get('years_relation') != 'not_stated']
            support.append(dict(split=s, object=label, reference_items=len(rs), numeric_reference_items=len(numeric),
                reference_unique_contexts=len({r['context_sha256'] for r in rs}),
                numeric_reference_unique_contexts=len({r['context_sha256'] for r in numeric}),
                candidate_covered_items=sum(bool(r['candidate_ids']) for r in numeric),
                compatible_candidates=len(compatible), compatible_unique_contexts=len({r['context_sha256'] for r in compatible}),
                primary_old_experience_compatible_candidates=len(primary_compatible),
                primary_old_experience_compatible_unique_contexts=len({r['context_sha256'] for r in primary_compatible}),
                reference_localization_states=dict(collections.Counter(r['localization_state'] for r in rs))))
    gates = []
    for label in classes:
        counts = {s: next(r['compatible_unique_contexts'] for r in support if r['split'] == s and r['object'] == label) for s in SPLITS}
        gates.append(dict(object=label, train_unique_contexts=counts[SPLITS[0]], final_unique_contexts=counts[SPLITS[1]],
            train50_final50_pass=counts[SPLITS[0]] >= 50 and counts[SPLITS[1]] >= 50))
    report = dict(version='year-object-original-same-item-binding-v1', scheduler_job_id=os.environ['SLURM_JOB_ID'],
        code_sha256=sha(__file__), input_manifest_sha256=sha(a.input_manifest),
        inputs=dict(contexts_sha256=sha(context_path), items_sha256=sha(item_path),
            rule_engine_sha256=a.expected_rule_sha256, legacy_sha256=a.expected_legacy_sha256),
        total_contexts=len(by_context), production_candidates=len(flat), original_year_reference_items=len(refs),
        global_year_candidates=len(flat),
        primary_old_experience_candidates=sum(r['primary_old_experience_candidate'] for r in flat),
        candidate_inventory_counts_by_split={s: dict(global_year_candidates=sum(r['split'] == s for r in flat),
            primary_old_experience_candidates=sum(r['split'] == s and r['primary_old_experience_candidate'] for r in flat),
            primary_old_experience_compatible_candidates=sum(r['split'] == s and r['primary_old_experience_candidate'] for r in fit + evaluation)) for s in SPLITS},
        train_compatible_candidates=len(fit), eval_compatible_candidates=len(evaluation),
        original_final_holdout_contexts=len(final), support_by_split_object=support, frozen_support_gate=gates,
        original_final_holdout_membership_sha256=membership_sha(final),
        context_membership_by_split={s: dict(count=sum(partition(c) == s for c in by_context),
            sorted_context_membership_sha256=membership_sha(c for c in by_context if partition(c) == s)) for s in SPLITS},
        compatible_context_membership_by_split={s: dict(count=len({r['context_sha256'] for r in associated if r['split'] == s and r['supervision_state'] == 'compatible_unique_reference'}),
            sorted_context_membership_sha256=membership_sha(r['context_sha256'] for r in associated if r['split'] == s and r['supervision_state'] == 'compatible_unique_reference')) for s in SPLITS},
        group_metadata=dict(recovered_context_metadata='context_sha256_and_complete_context_only',
            original_group_exposure='approved_analysis_frame_context_group_if_supplied; same_context_conflicts_unknown',
            inventory_provenance=inventory_provenance,
            reference_group_counts=dict(collections.Counter(r['reference_group'] for r in context_states)),
            inventory_eligible_contexts=sum(r['inventory_eligible'] for r in context_states),
            conflicting_group_contexts=sum(r['reference_group_conflict'] for r in context_states),
            reference_group_labels=dict(GA=GA, GB=GB),
            frozen_technology_flags='existing_rule_observed_mention_flags_attached_per_candidate; nondetection_not_semantic_absence'),
        context_states=dict(collections.Counter(r['state'] for r in context_states)),
        candidate_supervision_states_by_split={s: dict(collections.Counter(r['supervision_state'] for r in associated if r['split'] == s)) for s in SPLITS},
        reference_localization_states=dict(collections.Counter(r['localization_state'] for r in refs)),
        label_classes=classes, generated_negative_examples=0, gold_no_relation_available=False,
        input_scheme=dict(radius_unicode_codepoints=RADIUS, markers=['[YEAR]', '[/YEAR]'], frozen_version=rule.VERSION,
            old_object_filter_used=False, candidate_windows_reference_independent=True,
            numeric_match='all_scalar_or_range_values_conserved_in_year_units; explicit_relation_contradictions_rejected'),
        limitations=['Support floor is necessary, not quality acceptance.',
            'Final is previously exposed; final1331 and every legacy holdout are excluded from training.',
            'Every original year-family item is retained; not_stated has no literal-year relation and is never negative.',
            'Unknown and unlabeled candidates never become negatives; no gold no_relation exists.',
            'Repeated evidence, candidate-to-multiple-items and item-to-multiple-candidates are not forced.',
            'Only accepted same-original-item object/year masks bind; old predicted object does not filter gold.',
            'Unmatched numeric references remain in numeric candidate coverage denominators.',
            'No corpus inference, new labels, parser changes, dictionary growth, sampling or model search.'])
    report['outputs'] = {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()}
    write(root / 'PREPARATION_PUBLIC.json', report)


if __name__ == '__main__':
    main()
