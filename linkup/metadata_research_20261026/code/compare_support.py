#!/usr/bin/env python3
"""Scheduled, fixed10k-only descriptive employer/SOC support comparison.

Reads existing narrow columns only. Never derives or changes semantic labels.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

KEY = ['JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW']
MAJORS = ('11', '13', '15', '17')
Q1 = ['experience_general_work', 'experience_occupation_task',
      'experience_industry_domain', 'experience_tool_specific']
Q2 = ['duty_any', 'duty_independent_judgment', 'duty_client_ownership',
      'duty_people_supervision', 'duty_training_mentoring']
GROUPS = {'A': 'genai_use_with_or_without_software',
          'B': 'traditional_software_use_no_ai'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def missing(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def boolean(x):
    """Strict nullable binary parser; notably bool('False') is never used."""
    if missing(x):
        return None
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)) and x in (0, 1):
        return int(x)
    if isinstance(x, str):
        if x in ('true', 'True', '1'):
            return 1
        if x in ('false', 'False', '0'):
            return 0
    raise ValueError('Nonbinary value in existing boolean/reference column')


def identity(x):
    if missing(x) or str(x).strip() == '':
        return None
    if isinstance(x, float):
        raise ValueError('Floating company identifier is not exact identity')
    return str(x)


def csvwrite(path, rows):
    if not rows:
        path.write_text('status\nempty\n')
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def counts(rows, outcome=None):
    out = {'ads': len(rows), 'contexts': len({r['context'] for r in rows}),
           'companies': len({r['company'] for r in rows if r['company'] is not None})}
    if outcome:
        values = [r[outcome] for r in rows]
        out.update(positive=sum(v == 1 for v in values),
                   known=sum(v is not None for v in values),
                   unknown=sum(v is None for v in values))
    return out


def rate(rows, outcome):
    z = counts(rows, outcome)
    z.update(point=z['positive'] / z['known'] if z['known'] else None,
             lower=z['positive'] / z['ads'] if z['ads'] else None,
             upper=(z['positive'] + z['unknown']) / z['ads'] if z['ads'] else None)
    return z


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--input', required=True)
    ap.add_argument('--spec', required=True)
    ap.add_argument('--join-receipt', required=True)
    ap.add_argument('--private-output', required=True)
    ap.add_argument('--public-output', required=True)
    a = ap.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Scheduled SCNet execution required: missing SLURM_JOB_ID')
    src, specpath = Path(a.input).resolve(), Path(a.spec).resolve()
    spec = json.loads(specpath.read_text())
    if spec.get('groups') != GROUPS or spec['Q1']['outcomes'] != Q1 or spec['Q2']['outcomes'] != Q2:
        raise RuntimeError('Frozen groups/outcomes differ from implemented comparison')
    eligible_col = spec['metadata_eligibility_column']
    conflict_col = spec['metadata_conflict_column']
    priv, pub = Path(a.private_output).resolve(), Path(a.public_output).resolve()
    if priv == pub or priv in pub.parents or pub in priv.parents:
        raise RuntimeError('Private and public output trees must be disjoint')
    if any((p / '.git').exists() for p in (priv, *priv.parents)):
        raise RuntimeError('Private cell tables cannot be written inside Git')
    if any(p.exists() and any(p.iterdir()) for p in (priv, pub)):
        raise RuntimeError('Refusing to overwrite nonempty output directory')
    source_sha, spec_sha = sha(src), sha(specpath)
    joinpath = Path(a.join_receipt).resolve()
    join_receipt = json.loads(joinpath.read_text())
    if (join_receipt.get('augmented_research_sha256') != source_sha
            or join_receipt.get('rows') != 10000
            or join_receipt.get('original_columns_preserved') is not True
            or join_receipt.get('original_keys_preserved') is not True):
        raise RuntimeError('Join receipt does not certify exact input/10000 ads/original labels and keys')
    import pyarrow.parquet as pq
    cols = list(dict.fromkeys(KEY + ['metadata_company_id', eligible_col, conflict_col,
         'OCCUPATION_MAJOR', 'technology_group', 'normalized_context_sha256',
         'graduate_or_noexperience'] + Q1 + Q2))
    table = pq.read_table(src, columns=cols)
    if table.num_rows != 10000:
        raise RuntimeError('Input must preserve exactly 10000 canonical ads')
    records = table.to_pylist()
    seen, rows = set(), []
    for x in records:
        if any(missing(x[k]) for k in KEY + ['normalized_context_sha256']):
            raise RuntimeError('Missing canonical key or context hash')
        key = tuple(str(x[k]) for k in KEY)
        if key in seen:
            raise RuntimeError('Duplicate canonical ad key')
        seen.add(key)
        company = identity(x['metadata_company_id'])
        major = None if missing(x['OCCUPATION_MAJOR']) else str(x['OCCUPATION_MAJOR'])
        eligible, conflict = boolean(x[eligible_col]), boolean(x[conflict_col])
        if eligible is None or conflict is None:
            raise RuntimeError('Metadata eligibility/conflict flags must be nonnullable')
        if eligible and (conflict or company is None):
            raise RuntimeError('Metadata eligibility contradicts required identity/support')
        group = None if missing(x['technology_group']) else str(x['technology_group'])
        r = dict(company=company, major=major, group=group, eligible=eligible,
                 conflict=conflict, context=str(x['normalized_context_sha256']))
        for outcome in Q1 + Q2 + ['graduate_or_noexperience']:
            r[outcome] = boolean(x[outcome])
        rows.append(r)
    cells = defaultdict(list)
    for r in rows:
        if r['eligible'] and r['major'] in MAJORS and r['group'] in GROUPS.values():
            cells[r['company'], r['major']].append(r)
    structural = {k: rr for k, rr in cells.items()
                  if all(any(r['group'] == g for r in rr) for g in GROUPS.values())}
    for p in (priv, pub):
        p.mkdir(parents=True, exist_ok=True)
    os.chmod(priv, 0o700)
    support, private, results, distributions = [], [], [], []
    # Counts at every stage overlap only where their definitions overlap explicitly.
    stages = [('all_fixed10k', rows),
              ('metadata_eligible', [r for r in rows if r['eligible']]),
              ('company_missing', [r for r in rows if r['company'] is None]),
              ('occupation_missing', [r for r in rows if r['major'] is None]),
              ('occupation_outside_fixed_majors', [r for r in rows if r['major'] is not None and r['major'] not in MAJORS]),
              ('metadata_conflict', [r for r in rows if r['conflict']]),
              ('technology_unknown', [r for r in rows if r['group'] is None]),
              ('known_other_technology', [r for r in rows if r['group'] is not None and r['group'] not in GROUPS.values()]),
              ('structural_support', [r for rr in structural.values() for r in rr])]
    for stage, rr in stages:
        for m in ('all', *MAJORS, 'missing_or_outside'):
            selected = rr if m == 'all' else [r for r in rr if (r['major'] == m if m in MAJORS else r['major'] not in MAJORS)]
            support.append(dict(section='coverage', stage=stage, major=m, **counts(selected)))
    for outcome in Q1 + Q2 + ['graduate_or_noexperience']:
        for m in ('all', *MAJORS, 'missing_or_outside'):
            selected = rows if m == 'all' else [r for r in rows if (r['major'] == m if m in MAJORS else r['major'] not in MAJORS)]
            support.append(dict(section='original_field_ledger', outcome=outcome, major=m,
                                **counts(selected, outcome)))
    for question, outcomes in [('Q1', Q1), ('Q2', Q2)]:
        for outcome in outcomes:
            parts = {}
            for m in MAJORS:
                retained = []
                for (company, major), rr in structural.items():
                    if major != m:
                        continue
                    if question == 'Q1':
                        arows = [r for r in rr if r['group'] == GROUPS['A']]
                        brows = [r for r in rr if r['group'] == GROUPS['B']]
                        ra, rb = rate(arows, outcome), rate(brows, outcome)
                        ok = ra['known'] > 0 and rb['known'] > 0
                        z = {'point': ra['point'] - rb['point'] if ok else None,
                             'lower': ra['lower'] - rb['upper'],
                             'upper': ra['upper'] - rb['lower']}
                        denom = len(rr)
                        details = {f'{g}_{k}': v for g, rv in [('A', ra), ('B', rb)] for k, v in rv.items()}
                    else:
                        er = [r for r in rr if r['graduate_or_noexperience'] == 1]
                        rv = rate(er, outcome)
                        ok, denom = rv['known'] > 0, len(er)
                        z = {k: rv[k] for k in ('point', 'lower', 'upper')}
                        details = {**rv, 'eligibility_positive': len(er),
                                   'eligibility_unknown': sum(r['graduate_or_noexperience'] is None for r in rr)}
                    record = dict(question=question, outcome=outcome, major=m,
                                  metadata_company_id=company, structural_ads=len(rr),
                                  retained=ok, weight_numerator=denom if ok else 0,
                                  status='retained' if ok else 'missing_known_denominator', **details,
                                  contrast_point=z['point'], bound_lower=z['lower'], bound_upper=z['upper'])
                    private.append(record)
                    if ok:
                        retained.append((record, rr, z))
                mass = sum(rec['weight_numerator'] for rec, _, _ in retained)
                part = {field: sum(rec['weight_numerator'] * z[field] for rec, _, z in retained) / mass if mass else None
                        for field in ('point', 'lower', 'upper')}
                parts[m] = part
                results.append(dict(question=question, outcome=outcome, scope='major_' + m,
                                    status='known_reference_support_only' if mass else 'no_usable_cells', **part))
                selected = [r for _, rr, _ in retained for r in rr]
                support.append(dict(section='outcome_support', question=question, outcome=outcome,
                    major=m, structural_cells=sum(k[1] == m for k in structural),
                    usable_cells=len(retained), excluded_cells=sum(k[1] == m for k in structural) - len(retained),
                    aggregation_mass=mass, **counts(selected)))
                for rec, rr, _ in retained:
                    rec['within_major_weight'] = rec['weight_numerator'] / mass
                    rec['overall_weight'] = .25 * rec['within_major_weight']
                    distributions.append(dict(question=question, outcome=outcome, major=m,
                         pooled_cell_ads=len(rr), aggregation_ads=rec['weight_numerator'],
                         known_ads=(rec.get('A_known', 0) + rec.get('B_known', 0)) if question == 'Q1' else rec['known'],
                         positive_ads=(rec.get('A_positive', 0) + rec.get('B_positive', 0)) if question == 'Q1' else rec['positive'],
                         A_known_ads=rec.get('A_known'), B_known_ads=rec.get('B_known'),
                         A_singleton=int(rec['A_ads'] == 1) if question == 'Q1' else None,
                         B_singleton=int(rec['B_ads'] == 1) if question == 'Q1' else None,
                         known_singleton=int(rec['known'] == 1) if question == 'Q2' else None,
                         A_zero_positive=int(rec['A_positive'] == 0) if question == 'Q1' else None,
                         B_zero_positive=int(rec['B_positive'] == 0) if question == 'Q1' else None,
                         pooled_zero_positive=int(rec['positive'] == 0) if question == 'Q2' else None))
                for group in ('A', 'B') if question == 'Q1' else ('pooled',):
                    group_rows = selected if group == 'pooled' else [r for r in selected if r['group'] == GROUPS[group]]
                    evaluated = group_rows if question == 'Q1' else [r for r in group_rows if r['graduate_or_noexperience'] == 1]
                    support.append(dict(section='outcome_counts', question=question, outcome=outcome, major=m,
                       group=group, eligibility_unknown=sum(r['graduate_or_noexperience'] is None for r in group_rows) if question == 'Q2' else None,
                       **counts(evaluated, outcome)))
            available = all(parts[m]['point'] is not None for m in MAJORS)
            results.append(dict(question=question, outcome=outcome, scope='equal_0.25_major_standardization',
                status='known_reference_support_only' if available else 'missing_required_major_no_renormalization',
                **{field: sum(parts[m][field] for m in MAJORS) / 4 if available else None for field in ('point', 'lower', 'upper')}))
    histogram = Counter(tuple(sorted(x.items())) for x in distributions)
    csvwrite(priv / 'CELL_SUPPORT_RESULTS_WEIGHTS_PRIVATE.csv', private)
    csvwrite(pub / 'SUPPORT_AND_EXCLUSIONS.csv', support)
    csvwrite(pub / 'Q1_Q2_DESCRIPTIVE_RESULTS.csv', results)
    csvwrite(pub / 'CELL_SIZE_AND_SPARSITY_DISTRIBUTION.csv', [{**dict(k), 'cells': n} for k, n in sorted(histogram.items(), key=lambda item: repr(item[0]))])
    if sha(src) != source_sha or sha(specpath) != spec_sha:
        raise RuntimeError('Input/spec changed during execution')
    receipt = dict(version='fixed10k-company-major-descriptive-v1', slurm_job_id=os.environ['SLURM_JOB_ID'],
        source_sha256=source_sha, spec_sha256=spec_sha, join_receipt_sha256=sha(joinpath), code_sha256=sha(Path(__file__)),
        input_ads=10000, canonical_keys_unique=True, read_columns=cols,
        labels_mutated=False, no_advertisement_text_read=True, weight=1,
        membership_validation='Exactly 10000 unique input canonical keys; exact input SHA bound to upstream receipt certifying original columns/keys preserved.',
        scope='Observed fixed10k employer/SOC-major reference-known support only; no parent/all-US inference.',
        bounds='Recorded outcome unknown only within retained cells and fixed weights; Q2 conditional on eligibility-positive; not full-target bounds or CIs.',
        reference='Unchanged operational Pro reference, not independent human gold.',
        limits='No new labels, family recomputation, models, CIs, causal claims, employer adoption, duty strength or historical change.',
        outputs={p.name: sha(p) for p in sorted(pub.glob('*.csv'))},
        private_output_sha256=sha(priv / 'CELL_SUPPORT_RESULTS_WEIGHTS_PRIVATE.csv'))
    (pub / 'COMPARISON_RECEIPT_PUBLIC.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
