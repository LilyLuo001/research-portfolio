#!/usr/bin/env python3
"""Frozen, field-local Stage5 machine-reference agreement. No model calls.

Only source-supported represented categories/relations are scored. This is not
an object-concept taxonomy or a parser of complete qualification logic.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/lilyluo/Documents/LinkUp_Research_20260924/reproducibility_git')
EXP = ('general_work', 'occupation_task', 'industry_domain', 'tool_specific')
ENTRY = ('explicit_no_experience', 'explicit_new_graduate',
         'current_student_internship', 'explicit_junior_or_entry_label')
RESP = ('independent_judgment', 'client_ownership', 'people_supervision', 'training_mentoring')
FAMILIES = {'experience': (EXP, 'experience_clauses', 'object'),
            'entry': (ENTRY, 'entry_items', 'target'),
            'responsibility': (RESP, 'responsibility_items', 'dimension')}


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest_json(value):
    return hashlib.sha256(stable(value).encode('utf-8')).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_units(text):
    """Pre-output Unicode-offset units; newlines, sentence ends and semicolons.

    No model, label, vocabulary or candidate output participates. IDs are
    document-local; context_sha256 binds their source. Unit text is not exported.
    """
    if not isinstance(text, str) or not text:
        raise ValueError('empty_source_document')
    units, start = [], 0
    for boundary in re.finditer(r'\n+|(?<=[.!?;])[ \t]+', text):
        end = boundary.start()
        if text[start:end].strip():
            units.append({'id': len(units), 'start': start, 'end': end})
        start = boundary.end()
    if text[start:].strip():
        units.append({'id': len(units), 'start': start, 'end': len(text)})
    return units


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator(repo=REPO, protocol=None):
    repo = Path(repo)
    protocol = protocol or json.loads((HERE / 'CONFIRMATION_PROTOCOL.json').read_text())
    for source in protocol['source_files']:
        if file_sha(repo / source['path']) != source['sha256']:
            raise ValueError('frozen_source_hash_mismatch:' + source['path'])
    schema = json.loads((repo / protocol['schema']).read_text())
    frozen = _module(repo / protocol['frozen_validator'], 'stage5_formal800_validator')
    adapter = _module(repo / protocol['field_validator'], 'stage5_field_adapter')
    return adapter.FieldValidator(schema, frozen)


def evidence(item, text, units, frozen):
    """All exact occurrences retained; no selected occurrence is invented."""
    spans, repeated = [], 0
    for quote in item['quotes']:
        occurrences = frozen.find_all(text, quote)
        if not occurrences:
            raise ValueError('evidence_missing')
        repeated += len(occurrences) > 1
        spans.extend((p['start'], p['end']) for p in occurrences)
    anchors = sorted({u['id'] for u in units for a, b in spans
                      if max(a, u['start']) < min(b, u['end'])})
    if not anchors:
        raise ValueError('evidence_without_source_unit')
    return {'units': anchors, 'spans': sorted(set(spans)), 'repeated_quotes': repeated}


def values(item, columns):
    result = {name: item[name] for name in columns}
    if any(value == 'unresolved' for value in result.values()):
        raise ValueError('unresolved_measure_component')
    return result


def atom(item, columns, text, units, frozen, scope=None):
    return {'values': values(item, columns),
            'evidence': evidence(item, text, units, frozen), 'scope': scope}


def group_scope(review, item, text, units, frozen):
    name = item['alternative_group']
    if name is None:
        return None
    matches = [g for g in review['qualification_alternatives'] if g['group'] == name]
    if len(matches) != 1 or matches[0]['relation'] == 'unresolved':
        raise ValueError('unresolved_represented_group')
    group = matches[0]
    branches = []
    columns = ('object', 'strength', 'conditionality', 'years_min', 'years_max', 'years_relation')
    for branch in group['branches']:
        claims = [atom(c, columns, text, units, frozen) for c in review['experience_clauses']
                  if c['alternative_group'] == name and c['alternative_branch'] == branch['branch']]
        branches.append({'selected': item['alternative_branch'] == branch['branch'],
                         'evidence': evidence(branch, text, units, frozen), 'claims': claims})
    shared = [atom(c, columns, text, units, frozen) for c in review['experience_clauses']
              if c['alternative_group'] == name and c['alternative_branch'] is None]
    return {'relation': group['relation'], 'shared_scope': item['alternative_branch'] is None,
            'branches': branches, 'shared_claims': shared}


def maximum_matches(left, right, compatible):
    """Deterministic maximum cardinality one-to-one matching, never many-to-one."""
    matched = {}
    def visit(i, seen):
        for j, candidate in enumerate(right):
            if j in seen or not compatible(left[i], candidate):
                continue
            seen.add(j)
            if j not in matched or visit(matched[j], seen):
                matched[j] = i
                return True
        return False
    for i in range(len(left)):
        visit(i, set())
    return len(matched)


def supported(a, b):
    return bool(set(a['units']) & set(b['units']))


def scope_equal(a, b):
    if a is None or b is None:
        return a is None and b is None
    if a['relation'] != b['relation'] or a['shared_scope'] != b['shared_scope']:
        return False
    def branch_equal(x, y):
        return (x['selected'] == y['selected'] and supported(x['evidence'], y['evidence'])
                and lists_equal(x['claims'], y['claims']))
    return (len(a['branches']) == len(b['branches'])
            and maximum_matches(a['branches'], b['branches'], branch_equal) == len(a['branches'])
            and lists_equal(a['shared_claims'], b['shared_claims']))


def compatible(a, b):
    return (a['values'] == b['values'] and supported(a['evidence'], b['evidence'])
            and scope_equal(a['scope'], b['scope']))


def lists_equal(a, b):
    return len(a) == len(b) and maximum_matches(a, b, compatible) == len(a)


def observe(review, validation, spec, packet, units, frozen, processing_status='unprocessed'):
    """Partial positives remain in source, but do not certify complete inventories."""
    if review is None:
        return {'status': processing_status, 'outcome': 'unknown', 'atoms': []}
    field = spec['field']
    local = validation.get('fields', {}).get(field, {})
    state = local.get('status', 'blocked_shared_input')
    if state != 'engineering_valid':
        return {'status': state, 'outcome': 'unknown', 'atoms': []}
    if review['document_status'] != 'reviewed_full':
        return {'status': 'reviewed_partial', 'outcome': 'unknown', 'atoms': []}
    family, _, dimension = field.partition('.')
    kind = spec['kind']
    if family == 'technology':
        items = review['technology_items']
        declared = {'explicit_mentions_recorded': 'present',
                    'not_mentioned_after_full_review': 'not_mentioned', 'unknown': 'unknown'}[
                        review['technology_inventory_status']]
    else:
        _, inventory, selector = FAMILIES[family]
        items = [i for i in review[inventory] if i[selector] == dimension]
        declared = review[family + '_outcomes'][dimension]
    text, claims = packet['full_document'], []
    waiver_count = sum(i.get('strength') == 'explicitly_waived' for i in items)
    try:
        if kind == 'mention':
            if family == 'experience':
                selected = [i for i in items if i['strength'] in ('required', 'preferred', 'unspecified')]
                columns = ('object',)
            elif family == 'responsibility':
                selected = [i for i in items if i['subject'] == 'advertised_worker'
                            and i['relation'] in ('current_duty', 'required_capability', 'prior_experience')]
                columns = ('dimension',)
            elif family == 'entry':
                selected, columns = items, ('target',)
            else:
                selected, columns = items, ()
            # Detection is document-level. Evidence is independently validated;
            # tuple support remains diagnostic for this coarse estimand.
            claims = [atom(i, columns, text, units, frozen) for i in selected]
            outcome = declared
        else:
            if family == 'experience':
                columns = {'years': ('object', 'years_min', 'years_max', 'years_relation'),
                           'strength': ('object', 'strength'),
                           'waiver': ('object', 'strength'),
                           'conditionality': ('object', 'conditionality'),
                           'group': ('object',),
                           'clause_relation': ('object', 'years_min', 'years_max', 'years_relation',
                                               'strength', 'conditionality')}[kind]
                selected = items
                if kind == 'years':
                    if any(i['years_relation'] == 'unresolved' for i in items):
                        raise ValueError('unresolved_measure_component')
                    selected = [i for i in items if i['years_relation'] != 'not_stated']
                elif kind == 'waiver':
                    if any(i['strength'] == 'unresolved' for i in items):
                        raise ValueError('unresolved_measure_component')
                    selected = [i for i in items if i['strength'] == 'explicitly_waived']
                elif kind == 'group':
                    selected = [i for i in items if i['alternative_group'] is not None]
                for i in selected:
                    scope = group_scope(review, i, text, units, frozen) if kind in (
                        'conditionality', 'group', 'clause_relation') else None
                    claims.append(atom(i, columns, text, units, frozen, scope))
            elif family == 'entry':
                claims = [atom(i, ('target', 'conditionality'), text, units, frozen) for i in items]
            elif family == 'responsibility':
                if kind == 'strict_current_duty':
                    if any(i['subject'] == 'unresolved' or i['relation'] == 'unresolved' for i in items):
                        raise ValueError('unresolved_measure_component')
                    items = [i for i in items if i['subject'] == 'advertised_worker'
                             and i['relation'] == 'current_duty']
                    columns = ('dimension', 'subject', 'relation')
                else:
                    columns = ('dimension', 'subject', 'relation', 'conditionality')
                claims = [atom(i, columns, text, units, frozen) for i in items]
            else:
                columns = ('family', 'role') if kind == 'family_role' else (
                    'technology', 'family', 'role', 'developed_object')
                claims = [atom(i, columns, text, units, frozen) for i in items]
            outcome = 'present' if claims else 'not_mentioned'
        # Collapse transport duplicates only. Distinct source units or values
        # remain separate, and different atoms cannot share a match.
        unique = {}
        for claim in claims:
            signature = stable({'values': claim['values'], 'units': claim['evidence']['units'],
                                'scope': claim['scope']})
            unique.setdefault(signature, claim)
        return {'status': 'known', 'outcome': outcome, 'atoms': list(unique.values()),
                'explicit_waiver_count': waiver_count}
    except (KeyError, TypeError, ValueError):
        return {'status': 'unresolved_measure_component', 'outcome': 'unknown', 'atoms': [],
                'explicit_waiver_count': waiver_count}


def rates(tp, fp, fn):
    return {'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def summarize(pairs, spec, gate, *, qualify):
    matrix, states, support, relation, strict = Counter(), Counter(), Counter(), Counter(), Counter()
    for reference, candidate in pairs:
        states['reference:' + reference['status']] += 1
        states['candidate:' + candidate['status']] += 1
        if reference['outcome'] == 'unknown':
            continue
        ro, co = reference['outcome'], candidate['outcome']
        support[ro] += 1
        matrix[ro, co] += 1
        ra = reference['atoms']
        ca = candidate['atoms'] if co != 'unknown' else []
        tp = maximum_matches(ra, ca, compatible)
        relation.update(tp=tp, fp=len(ca) - tp, fn=len(ra) - tp)
        exact = maximum_matches(ra, ca, lambda a, b: compatible(a, b)
                                and a['evidence']['spans'] == b['evidence']['spans'])
        strict.update(tp=exact, fp=len(ca) - exact, fn=len(ra) - exact)
    classes = {label: rates(matrix[label, label],
                           sum(n for (r, p), n in matrix.items() if p == label and r != label),
                           sum(n for (r, p), n in matrix.items() if r == label and p != label))
               for label in ('present', 'not_mentioned')}
    macro = sum(c['f1'] or 0.0 for c in classes.values()) / 2
    claims = rates(relation['tp'], relation['fp'], relation['fn'])
    known, total = sum(support.values()), len(pairs)
    coverage = known / total if total else 0.0
    reasons = []
    for failed, reason in (
        (coverage < gate['known_reference_coverage_min'], 'known_reference_coverage_below_gate'),
        (known < gate['minimum_known_cases_per_field'], 'insufficient_known_cases'),
        (support['present'] < gate['minimum_positive_cases_per_field'], 'insufficient_positive_cases'),
        (support['not_mentioned'] < gate['minimum_negative_cases_per_field'], 'insufficient_negative_cases'),
        (macro < gate['macro_f1_min'], 'outcome_macro_f1_below_gate')):
        if failed:
            reasons.append(reason)
    for metric in ('precision', 'recall'):
        score = classes['present'][metric]
        if score is None or score < gate[metric + '_min']:
            reasons.append('outcome_' + metric + '_below_gate')
    if spec['require_claim_agreement']:
        for metric, threshold in (('precision', 'precision_min'), ('recall', 'recall_min'),
                                  ('f1', 'macro_f1_min')):
            if claims[metric] is None or claims[metric] < gate[threshold]:
                reasons.append('supported_relation_' + metric + '_below_gate')
    if not qualify:
        reasons.append('challenge_diagnostic_only')
    return {'cases': total, 'known_reference_cases': known, 'known_reference_coverage': coverage,
            'unknown_reference_cases': total - known, 'support': dict(support),
            'status_counts': dict(states),
            'confusion_matrix': [{'reference': r, 'candidate': c, 'n': n}
                                 for (r, c), n in sorted(matrix.items())],
            'class_metrics': classes, 'outcome_macro_f1': macro,
            'source_unit_supported_relation': claims,
            'exact_quote_span_diagnostic_not_gate': rates(strict['tp'], strict['fp'], strict['fn']),
            'machine_reference_measure_gate_pass': not reasons,
            'blocking_reasons': reasons}


def evaluate(frame, cases, protocol, validator):
    """Metadata frame is trusted and frozen first; never silently drop failures.

    Missing case/output rows become unprocessed. A trusted protection_blocked flag
    is checked before packet/review access. Existing payloads are never rewritten.
    """
    if not 0 < len(frame) <= protocol['authorization']['fresh_input_cap']:
        raise ValueError('confirmation_frame_size_out_of_bounds')
    expected = {r['record_id']: r for r in frame}
    if len(expected) != len(frame) or len({r['context_sha256'] for r in frame}) != len(frame):
        raise ValueError('duplicate_frame_identity_or_context')
    for row in frame:
        if row.get('protected') is not False or row.get('fresh_never_exposed') is not True:
            raise ValueError('ineligible_frozen_frame')
        if row['partition'] not in ('confirmation', 'challenge'):
            raise ValueError('invalid_frame_partition')
    actual = {r['record_id']: r for r in cases}
    if len(actual) != len(cases) or set(actual) - set(expected):
        raise ValueError('duplicate_or_out_of_frame_case')
    pools = {name: {s['id']: [] for s in protocol['measures']} for name in ('confirmation', 'challenge')}
    accounting = Counter()
    audit_candidates = []
    for record_id, metadata in expected.items():
        case = actual.get(record_id, {'record_id': record_id})
        blocked = case.get('protection_blocked', False)
        if not isinstance(blocked, bool):
            raise ValueError('trusted_protection_flag_required')
        if blocked:
            # Do not inspect packet or either review for protected cases.
            packet, reviews, validations, units = None, [None, None], [{}, {}], []
            statuses = ['quarantined', 'quarantined']
        else:
            packet = case.get('packet')
            reviews = [case.get('reference'), case.get('candidate')]
            statuses = [case.get('reference_processing_status', 'unprocessed'),
                        case.get('candidate_processing_status', 'unprocessed')]
            bound = (isinstance(packet, dict) and packet.get('record_id') == record_id
                     and packet.get('context_sha256') == metadata['context_sha256']
                     and case.get('context_sha256', metadata['context_sha256']) == metadata['context_sha256'])
            try:
                units = source_units(packet['full_document']) if bound else []
                bound = bound and digest_json(units) == metadata['source_units_sha256']
            except (KeyError, TypeError, ValueError):
                bound, units = False, []
            if bound:
                validations = [validator.validate(packet, r, protected=False) if r is not None else {}
                               for r in reviews]
            else:
                validations = [{}, {}]
                statuses = ['shared_input_invalid' if r is not None else s for r, s in zip(reviews, statuses)]
                reviews = [None, None]
        accounting['frame_cases'] += 1
        accounting['missing_case_rows'] += record_id not in actual
        accounting['quarantined_after_freeze'] += blocked
        audit_reasons = []
        for spec in protocol['measures']:
            observations = [observe(r, v, spec, packet, units, validator.frozen, status)
                            for r, v, status in zip(reviews, validations, statuses)]
            pools[metadata['partition']][spec['id']].append(observations)
            reference, candidate = observations
            semantically_unknown_reference = reference['status'] in (
                'reviewed_unknown', 'unresolved_measure_component')
            known_disagreement = (reference['status'] == candidate['status'] == 'known'
                                  and (reference['outcome'] != candidate['outcome'] or
                                       (spec['require_claim_agreement'] and not lists_equal(
                                           reference['atoms'], candidate['atoms']))))
            if not blocked and (semantically_unknown_reference or known_disagreement):
                audit_reasons.append(spec['id'])
        if audit_reasons:
            audit_candidates.append({'record_id': record_id,
                                     'context_sha256': metadata['context_sha256'],
                                     'rank_sha256': digest_json([protocol['version'], record_id,
                                                                 metadata['context_sha256']]),
                                     'measure_ids': audit_reasons})
    results = {name: {s['id']: summarize(pool[s['id']], s, protocol['gate'], qualify=name == 'confirmation')
                      for s in protocol['measures']} for name, pool in pools.items()}
    eligible = [name for name, result in results['confirmation'].items()
                if result['machine_reference_measure_gate_pass']]
    audit_candidates.sort(key=lambda r: (r['rank_sha256'], r['record_id']))
    return {'protocol_version': protocol['version'], 'accounting': dict(accounting),
            'measure_results': results, 'eligible_measure_dependencies': eligible,
            'bounded_astra_diagnostic_queue': audit_candidates[:protocol['authorization']['astra_adjudication_cases_max']],
            'astra_queue_does_not_authorize_spend_or_modify_primary_reference': True,
            'modules_retained': protocol['modules'],
            'not_qualified_by_this_test': protocol['not_qualified_by_this_test'],
            'machine_reference_agreement_is_not_gold_accuracy': True,
            'population_generalization_certified': False, 'production_admission': False,
            'production_requires_qualified_dependency_subset_and_external_runtime_controls': True}


def _read_jsonl(path):
    # Same strict JSON decoder used by the existing local adapter.
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite_json_number')
    rows = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            row = json.loads(line, object_pairs_hook=pairs, parse_constant=invalid)
            if not isinstance(row, dict):
                raise ValueError('jsonl_row_not_object')
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--frame-freeze', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=REPO)
    args = parser.parse_args()
    protocol_path = HERE / 'CONFIRMATION_PROTOCOL.json'
    protocol = json.loads(protocol_path.read_text())
    receipt = json.loads(args.frame_freeze.read_text())
    bundle = json.loads((HERE / 'PROTOCOL_FREEZE.json').read_text())
    for name, digest in bundle['files'].items():
        if file_sha(HERE / name) != digest:
            raise ValueError('protocol_bundle_modified:' + name)
    required = {'frame_sha256': file_sha(args.frame),
                'protocol_bundle_sha256': file_sha(HERE / 'PROTOCOL_FREEZE.json'),
                'frozen_before_first_request': True}
    if any(receipt.get(k) != v for k, v in required.items()):
        raise ValueError('frame_not_bound_to_preoutput_protocol_freeze')
    frame = _read_jsonl(args.frame)
    result = evaluate(frame, _read_jsonl(args.cases), protocol, load_validator(args.repo, protocol))
    result['freeze_binding'] = required
    # New output only; no accidental overwrite of historical results.
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
