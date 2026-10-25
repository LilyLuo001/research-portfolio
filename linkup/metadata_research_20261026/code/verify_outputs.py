#!/usr/bin/env python3
"""Scheduled assertions only; never emits private values or alternate estimates."""
import argparse
import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path
import pyarrow.parquet as pq

MAJORS = ('11', '13', '15', '17')
OUTCOMES = {'Q1': ('experience_general_work', 'experience_occupation_task',
                  'experience_industry_domain', 'experience_tool_specific'),
            'Q2': ('duty_any', 'duty_independent_judgment', 'duty_client_ownership',
                   'duty_people_supervision', 'duty_training_mentoring')}
GROUPS = ('genai_use_with_or_without_software', 'traditional_software_use_no_ai')
KEY = ['JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW']


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def number(value):
    if value in ('', None):
        return None
    x = float(value)
    require(math.isfinite(x), 'nonfinite_numeric_output')
    return x


def equal(actual, expected):
    x = number(actual)
    require((x is None and expected is None) or
            (x is not None and expected is not None and
             math.isclose(x, expected, rel_tol=1e-10, abs_tol=1e-12)), 'numeric_formula_mismatch')


def binary(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    require(isinstance(x, (int, float, bool)) and x in (0, 1), 'nonbinary_source_field')
    return int(x)


def readcsv(path):
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    require(not any('ci_' in x.lower() or 'confidence' in x.lower() for x in fields), 'unintended_inference_column')
    return fields, rows


def verify(a):
    require(bool(os.environ.get('SLURM_JOB_ID')), 'scheduled_job_required')
    original, research, join = map(Path, (a.original_bridge, a.research, a.join_receipt))
    private, public = map(Path, (a.comparison_private, a.comparison_public))
    jr = json.loads(join.read_text())
    crpath = public.parent / 'COMPARISON_RECEIPT_PUBLIC.json'
    cr = json.loads(crpath.read_text())
    require(jr.get('status') == 'pass' and jr.get('input_bridge_sha256') == sha(original)
            and jr.get('augmented_research_sha256') == sha(research), 'join_input_hash_binding')
    require(jr.get('original_columns_preserved') is True and jr.get('original_keys_preserved') is True
            and jr.get('rows') == 10000, 'join_preservation_receipt')
    require(cr.get('source_sha256') == sha(research) and cr.get('join_receipt_sha256') == sha(join)
            and cr.get('private_output_sha256') == sha(private)
            and cr.get('outputs', {}).get(public.name) == sha(public), 'comparison_hash_binding')
    require(cr.get('input_ads') == 10000 and cr.get('labels_mutated') is False
            and cr.get('no_advertisement_text_read') is True and cr.get('weight') == 1, 'comparison_scope_receipt')
    old = pq.read_table(original)
    extra = ['metadata_company_id', 'metadata_company_valid', 'metadata_conflict',
             'metadata_conflict_fields', 'metadata_candidate_matches', 'metadata_records_matches']
    new = pq.read_table(research, columns=old.column_names + extra)
    require(old.num_rows == new.num_rows == 10000 and new.select(old.column_names).equals(old)
            and new.select(old.column_names).schema.equals(old.schema), 'original_arrow_preservation')
    rows = new.to_pylist()
    require(len({tuple(r[k] for k in KEY) for r in rows}) == 10000, 'original_membership_uniqueness')
    cells = defaultdict(list)
    for r in rows:
        conflict = r['metadata_conflict']
        valid = r['metadata_company_valid']
        require(type(conflict) is bool and type(valid) is bool
                and conflict == bool(r['metadata_conflict_fields']), 'metadata_boolean_consistency')
        company = r['metadata_company_id']
        require(company is None or (isinstance(company, str) and bool(company.strip())), 'company_identity_type')
        expected = company is not None and r['metadata_candidate_matches'] <= 1 and r['metadata_records_matches'] <= 1 and not conflict
        require(valid == expected and r['metadata_candidate_matches'] >= 0 and r['metadata_records_matches'] >= 0,
                'company_eligibility_consistency')
        if valid and r['OCCUPATION_MAJOR'] in MAJORS and r['technology_group'] in GROUPS:
            cells[company, r['OCCUPATION_MAJOR']].append(r)
    structural = {k: v for k, v in cells.items() if {r['technology_group'] for r in v} == set(GROUPS)}
    _, archived = readcsv(private)
    if archived == [{'status': 'empty'}]:
        archived = []
    expected_keys = {(q, o, m, c) for c, m in structural for q, oo in OUTCOMES.items() for o in oo}
    require(len(archived) == len(expected_keys) and
            {(r['question'], r['outcome'], r['major'], r['metadata_company_id']) for r in archived} == expected_keys,
            'private_cell_membership')
    retained = defaultdict(list)
    for rec in archived:
        q, o, m, c = (rec[k] for k in ('question', 'outcome', 'major', 'metadata_company_id'))
        rr = structural[c, m]
        equal(rec['structural_ads'], len(rr))
        subsets = [[r for r in rr if r['technology_group'] == g] for g in GROUPS] if q == 'Q1' else [[r for r in rr if binary(r['graduate_or_noexperience']) == 1]]
        rates = []
        for prefix, subset in zip(('A_', 'B_') if q == 'Q1' else ('',), subsets):
            values = [binary(r[o]) for r in subset]
            n, known, positive = len(values), sum(x is not None for x in values), sum(x == 1 for x in values)
            for field, value in [('ads', n), ('known', known), ('unknown', n-known), ('positive', positive),
                                 ('contexts', len({r['normalized_context_sha256'] for r in subset})),
                                 ('companies', len({r['metadata_company_id'] for r in subset}))]:
                equal(rec[prefix+field], value)
            rates.append((positive/known if known else None, positive/n if n else None,
                          (positive+n-known)/n if n else None))
            for field, value in zip(('point', 'lower', 'upper'), rates[-1]):
                equal(rec[prefix+field], value)
        if q == 'Q2':
            equal(rec['eligibility_positive'], len(subsets[0]))
            equal(rec['eligibility_unknown'], sum(binary(r['graduate_or_noexperience']) is None for r in rr))
        ok = all(x[0] is not None for x in rates)
        require(rec['retained'] == str(ok), 'zero_known_retention')
        require(rec['status'] == ('retained' if ok else 'missing_known_denominator'), 'cell_status')
        mass = len(rr) if q == 'Q1' else len(subsets[0])
        equal(rec['weight_numerator'], mass if ok else 0)
        point = rates[0][0]-rates[1][0] if q == 'Q1' and ok else rates[0][0] if q == 'Q2' else None
        lower = rates[0][1]-rates[1][2] if q == 'Q1' else rates[0][1]
        upper = rates[0][2]-rates[1][1] if q == 'Q1' else rates[0][2]
        for field, value in zip(('contrast_point', 'bound_lower', 'bound_upper'), (point, lower, upper)):
            equal(rec[field], value)
        if ok:
            require(lower-1e-12 <= point <= upper+1e-12, 'cell_bounds_containment')
            retained[q, o, m].append((rec, mass, (point, lower, upper)))
        else:
            equal(rec.get('within_major_weight'), None)
            equal(rec.get('overall_weight'), None)
    fields, published = readcsv(public)
    require(set(fields) == {'question', 'outcome', 'scope', 'status', 'point', 'lower', 'upper'}, 'public_numeric_columns')
    target = {}
    for q, oo in OUTCOMES.items():
        for o in oo:
            parts = []
            for m in MAJORS:
                selected = retained[q, o, m]
                total = sum(x[1] for x in selected)
                for rec, mass, _ in selected:
                    equal(rec['within_major_weight'], mass/total)
                    equal(rec['overall_weight'], .25*mass/total)
                if total:
                    equal(sum(number(x[0]['within_major_weight']) for x in selected), 1)
                values = tuple(sum(mass*z[i] for _, mass, z in selected)/total for i in range(3)) if total else (None,)*3
                target[q, o, 'major_'+m] = (values, 'known_reference_support_only' if total else 'no_usable_cells')
                parts.append(values)
            ok = all(v[0] is not None for v in parts)
            target[q, o, 'equal_0.25_major_standardization'] = (tuple(sum(v[i] for v in parts)/4 for i in range(3)) if ok else (None,)*3,
                'known_reference_support_only' if ok else 'missing_required_major_no_renormalization')
    require(len(published) == len(target) and {(r['question'], r['outcome'], r['scope']) for r in published} == set(target), 'public_result_membership')
    for rec in published:
        values, status = target[rec['question'], rec['outcome'], rec['scope']]
        require(rec['status'] == status, 'public_availability_status')
        for field, value in zip(('point', 'lower', 'upper'), values):
            equal(rec[field], value)
        if values[0] is not None:
            require(values[1]-1e-12 <= values[0] <= values[2]+1e-12, 'public_bounds_containment')
    return {'original_bridge': sha(original), 'research': sha(research), 'join_receipt': sha(join),
            'comparison_receipt': sha(crpath), 'comparison_private': sha(private), 'comparison_public': sha(public)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('original-bridge', 'research', 'join-receipt', 'comparison-private', 'comparison-public', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    report = {'status': 'fail', 'reference_quality_certified': False, 'new_estimates_emitted': False}
    try:
        report.update(input_sha256=verify(args), status='pass', reasons=['all_numeric_and_provenance_assertions_passed'])
    except Exception as error:
        report['reasons'] = [str(error) if isinstance(error, AssertionError) else 'verification_execution_error_'+type(error).__name__]
    report.update(slurm_job_id=os.environ.get('SLURM_JOB_ID'), code_sha256=sha(__file__))
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    raise SystemExit(0 if report['status'] == 'pass' else 1)
