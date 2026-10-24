#!/usr/bin/env python3
"""Scheduled metadata/narrow-column design correction for frozen fixed10k.

The CLI reads no advertisement bodies/evidence quotes, changes no labels, and
never reads Formal800 weights. All row-level artifacts are private.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import duckdb
from correction_core import (MAJORS, GA, GB, expr, needed_columns, conjunction,
    estimate_component, corrected_point, known_domain_components, ht_envelope, design_variance)

KEY = ['JOB_HASH', 'SOURCE_FILE', 'SOURCE_ROW', 'RECORD_SOURCE_ROW']
CELL = ['OCCUPATION_MAJOR', 'CENSUS_REGION', 'created_year', 'arm']
EXP = ('general_work', 'occupation_task', 'industry_domain', 'tool_specific')
DUTY = ('independent_judgment', 'client_ownership', 'people_supervision', 'training_mentoring')
VERSION = 'frozen-fixed10k-design-correction-v1'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def qid(x):
    return '"' + x.replace('"', '""') + '"'


def qstr(x):
    return "'" + str(x).replace("'", "''") + "'"


def canonical(frame):
    if frame[KEY].isna().any().any():
        raise RuntimeError('null canonical ad key')
    for name in KEY[:2]:
        frame[name] = frame[name].astype(str)
    for name in KEY[2:]:
        frame[name] = pd.to_numeric(frame[name], errors='raise').astype('int64')
    if frame[KEY].isna().any().any() or frame.duplicated(KEY).any():
        raise RuntimeError('invalid or duplicate canonical ad key')
    return frame


def default_spec(available):
    measures = []
    oldmap = {'general_work': 'general_work', 'industry_domain': 'industry_domain', 'tool_specific': 'specific_tool'}
    for obj in EXP:
        measures.append(('experience_' + obj, 'exp_' + oldmap[obj] + '_main' if obj in oldmap else None))
        for attr in ('required', 'preferred', 'explicitly_waived'):
            measures.append((f'strength_{obj}_{attr}', f'exp_{oldmap[obj]}_{attr}' if obj in oldmap and attr in ('required', 'preferred') else None))
        for attr in ('numeric_years', 'conditional', 'alternative_branch', 'alternative_or_branch', 'alternative_and_branch'):
            measures.append((attr + '_' + obj, None))
    domains = {'all_technology': True, GA: {'op': 'eq', 'column': 'technology_group', 'value': GA},
               GB: {'op': 'eq', 'column': 'technology_group', 'value': GB}}
    old_domains = {'all_technology': True, GA: {'op': 'eq', 'column': 'arm', 'value': 'A'},
                   GB: {'op': 'eq', 'column': 'arm', 'value': 'B'}}
    specs = []
    for measure, proxy in measures:
        if measure not in available:
            raise RuntimeError('missing frozen reference measure: ' + measure)
        for domain in (GA, GB):
            specs.append(dict(question='Q1', domain=domain, eligibility='all_ads', measure=measure,
                reference_domain=domains[domain], old_domain=old_domains[domain],
                old_outcome=proxy if proxy else False,
                proxy_kind='frozen_old_candidate_proxy' if proxy else 'zero_auxiliary_no_old_comparator',
                old_comparator_available=proxy is not None))
    entry = ('explicit_new_graduate', 'explicit_no_experience', 'graduate_or_noexperience',
             'explicit_new_graduate_unconditional', 'explicit_no_experience_unconditional', 'graduate_or_noexperience_unconditional')
    q2_measures = ['duty_' + d for d in (*DUTY, 'any')]
    q2_measures += ['duty_' + d + '_' + c for d in (*DUTY, 'any') for c in ('conditional', 'unconditional')]
    q2_measures += ['experience_' + e for e in EXP]
    for eligibility in entry:
        for measure in q2_measures:
            if measure not in available or eligibility not in available:
                raise RuntimeError('missing frozen Q2 reference column')
            for domain in domains:
                specs.append(dict(question='Q2', domain=domain, eligibility=eligibility, measure=measure,
                    reference_domain={'op': 'and', 'args': [domains[domain], eligibility]},
                    old_domain=False, old_outcome=False,
                    proxy_kind='zero_auxiliary_no_old_comparator', old_comparator_available=False))
    return specs


def cell_tuples(frame):
    f = frame[CELL].copy()
    f['OCCUPATION_MAJOR'] = f['OCCUPATION_MAJOR'].astype(str)
    f['CENSUS_REGION'] = f['CENSUS_REGION'].astype(str)
    f['created_year'] = f['created_year'].astype(int).astype(str)
    f['arm'] = f['arm'].astype(str)
    return list(f.itertuples(index=False, name=None))


def safe_private(path):
    path = Path(path).resolve()
    if any((x / '.git').exists() for x in (path, *path.parents)):
        raise RuntimeError('private data output cannot be inside Git')
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parent', action='append', required=True, help='exact original 16 candidate-joined narrow Parquet partitions; repeat')
    ap.add_argument('--fixed', required=True)
    ap.add_argument('--reference', required=True)
    ap.add_argument('--allocation', required=True)
    ap.add_argument('--reference-receipt', required=True, help='accepted fixed10k empirical receipt binding this exact reference parquet')
    ap.add_argument('--isolation-register', required=True, help='frozen metadata-only 14-context isolation register')
    ap.add_argument('--spec', help='optional root-reviewed JSON list overriding only frozen proxy mappings')
    ap.add_argument('--private-output', required=True)
    ap.add_argument('--public-output', required=True)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--memory-limit', default='12GB')
    ap.add_argument('--enable-design-se', action='store_true', help='requires acceptance of exchangeable independent salted-hash SRS assumption')
    a = ap.parse_args()
    priv = safe_private(a.private_output)
    out = Path(a.public_output); out.mkdir(parents=True, exist_ok=True)
    if (out / 'RUN_RECEIPT_PUBLIC.json').exists():
        raise RuntimeError('completed-output guard')
    paths = sorted(set(a.parent))
    if len(paths) != 16:
        raise RuntimeError('parent source must be the original exact 16 joined partitions')
    reference_receipt = json.loads(Path(a.reference_receipt).read_text())
    if reference_receipt.get('status') != 'pass' or reference_receipt.get('private_output', {}).get('sha256') != sha(a.reference):
        raise RuntimeError('reference parquet not bound to accepted empirical receipt')
    isolated_contexts = set()
    with open(a.isolation_register) as handle:
        for line in handle:
            isolated_contexts.add(json.loads(line)['normalized_context_sha256'])
    if len(isolated_contexts) != 14:
        raise RuntimeError('isolation register must preserve exact 14 frozen contexts')
    ref_schema = set(pq.ParquetFile(a.reference).schema_arrow.names)
    specs = json.loads(Path(a.spec).read_text()) if a.spec else default_spec(ref_schema)
    if not specs:
        raise RuntimeError('empty specifications')
    ref_cols = set(KEY + ['technology_group', 'occupation_major', 'original9282eligible', 'normalized_context_sha256'])
    ref_cols |= {c for c in ref_schema if c.startswith('status_')}
    for spec in specs:
        ref_cols |= needed_columns(spec['reference_domain']) | {spec['measure']}
    ref = canonical(pd.read_parquet(a.reference, columns=sorted(ref_cols)))
    isolated_ads = ref['normalized_context_sha256'].isin(isolated_contexts)
    if set(ref.loc[isolated_ads, 'normalized_context_sha256']) != isolated_contexts:
        raise RuntimeError('not all 14 isolated contexts preserved in ad bridge')
    # The existing technology mapper uses a named unresolved group, not null.
    ref.loc[ref['technology_group'] == 'uncertain_technology', 'technology_group'] = pd.NA
    fixed_cols = KEY + CELL + ['total_inclusion_probability', 'nested_design_weight', 'original_inclusion_probability', 'conditional_inclusion_probability']
    fixed = canonical(pd.read_parquet(a.fixed, columns=fixed_cols))
    if len(fixed) != 10000 or len(ref) != 10000 or fixed['arm'].value_counts().to_dict() != {'A': 4000, 'B': 4000, 'C': 2000}:
        raise RuntimeError('fixed frame counts differ')
    if int((~ref['original9282eligible'].astype(bool)).sum()) != 718:
        raise RuntimeError('prior-exposure accounting differs from 718')
    pi = fixed['total_inclusion_probability'].to_numpy(float)
    w = fixed['nested_design_weight'].to_numpy(float)
    if not (np.isfinite(w).all() and np.isfinite(pi).all() and (pi > 0).all() and (pi <= 1).all() and np.allclose(pi * w, 1., atol=1e-8, rtol=0)):
        raise RuntimeError('dedicated design weight invalid')
    if not np.allclose(pi, fixed['original_inclusion_probability'] * fixed['conditional_inclusion_probability'], atol=1e-10, rtol=0):
        raise RuntimeError('nested probability product invalid')
    alloc = pd.read_csv(a.allocation, dtype={'OCCUPATION_MAJOR': str, 'CENSUS_REGION': str, 'arm': str})
    alloc_cells = cell_tuples(alloc)
    if len(alloc) != 207 or len(set(alloc_cells)) != 207:
        raise RuntimeError('allocation must be exactly 207 distinct arm cells')
    sample_cells = cell_tuples(fixed)
    sample_n = pd.Series(sample_cells).value_counts().to_dict()
    population = {}
    for idx, cell in enumerate(alloc_cells):
        r = alloc.iloc[idx]
        N = float(r['frame_cell_arm_N']) / float(r['original_inclusion_probability'])
        if not np.isclose(N, round(N), atol=1e-6, rtol=0):
            raise RuntimeError('nonintegral reconstructed parent population')
        population[cell] = int(round(N))
        if sample_n.get(cell) != int(r['selected_cell_arm_n']):
            raise RuntimeError('sample allocation n mismatch')
    if sum(population.values()) != 1157573:
        raise RuntimeError('target parent population differs from 1157573')
    for cell, weight in zip(sample_cells, w):
        if not np.isclose(weight, population[cell] / sample_n[cell], rtol=1e-9, atol=1e-8):
            raise RuntimeError('nested design does not collapse to same-cell n/N')
    con = duckdb.connect(str(priv / 'work.duckdb'))
    con.execute('SET threads=' + str(a.threads)); con.execute('SET memory_limit=' + qstr(a.memory_limit))
    con.execute('SET temp_directory=' + qstr(priv / 'tmp'))
    con.read_parquet(paths, union_by_name=False).create_view('source_parent')
    support = alloc[['OCCUPATION_MAJOR', 'CENSUS_REGION', 'created_year']].drop_duplicates()
    con.register('support', support)
    # Original old C1 arm precedence, exactly as the accepted sampler.
    arm_sql = "CASE WHEN tech_generative_ai_use_explicit=true THEN 'A' WHEN tech_traditional_software_use_explicit=true AND tech_generative_ai_detected=false AND tech_predictive_ai_detected=false AND tech_unspecified_ai_detected=false THEN 'B' ELSE 'C' END"
    oldcols = set()
    for spec in specs:
        oldcols |= needed_columns(spec['old_domain']) | needed_columns(spec['old_outcome'])
    columns = sorted((oldcols | set(KEY + ['OCCUPATION_MAJOR', 'CENSUS_REGION'])) - {'arm'})
    projection = ','.join('j.' + qid(x) for x in columns)
    con.execute(f'''CREATE OR REPLACE VIEW parent AS SELECT {projection}, year(CAST(j.CREATED AS DATE))::INTEGER created_year,
        {arm_sql} arm FROM source_parent j JOIN support s ON CAST(j.OCCUPATION_MAJOR AS VARCHAR)=s.OCCUPATION_MAJOR
        AND CAST(j.CENSUS_REGION AS VARCHAR)=s.CENSUS_REGION AND year(CAST(j.CREATED AS DATE))=s.created_year
        WHERE j.usable=true AND CAST(j.CREATED AS DATE) BETWEEN DATE '2018-01-01' AND DATE '2026-06-30' ''')
    observed = con.execute('SELECT OCCUPATION_MAJOR,CENSUS_REGION,created_year,arm,count(*) n FROM parent GROUP BY 1,2,3,4').fetchdf()
    observed_n = dict(zip(cell_tuples(observed), observed['n'].astype(int)))
    if observed_n != population:
        raise RuntimeError('exact parent census does not reproduce all 207 cell populations')
    census_exprs = ['sum(CAST(' + qid(c) + ' AS BIGINT)) AS ' + qid(c + '_proxy_count') for c in sorted(oldcols - {'arm'})]
    census_sql = 'SELECT OCCUPATION_MAJOR,CENSUS_REGION,created_year,arm,count(*) AS parent_n' + (',' + ','.join(census_exprs) if census_exprs else '') + ' FROM parent GROUP BY 1,2,3,4'
    con.execute(census_sql).fetchdf().to_csv(out / 'OLD_207_CELL_CENSUS.csv', index=False)
    unique_n = con.execute('SELECT count(*) FROM (SELECT DISTINCT ' + ','.join(map(qid, KEY)) + ' FROM parent)').fetchone()[0]
    if unique_n != 1157573:
        raise RuntimeError('parent canonical keys not unique')
    con.register('sample_keys', fixed[KEY])
    oldsample = canonical(con.execute('SELECT p.* FROM parent p JOIN sample_keys s USING (' + ','.join(map(qid, KEY)) + ')').fetchdf())
    joined = fixed.merge(ref, on=KEY, validate='one_to_one', suffixes=('', '_reference')).merge(oldsample, on=KEY, validate='one_to_one', suffixes=('', '_old'))
    if len(joined) != 10000:
        raise RuntimeError('sample-to-reference-to-old bridge not exact 10000')
    for name in CELL:
        if name + '_old' in joined and not (joined[name].astype(str) == joined[name + '_old'].astype(str)).all():
            raise RuntimeError('sample and parent metadata disagree: ' + name)
    if not (joined['OCCUPATION_MAJOR'].astype(str) == joined['occupation_major'].astype(str)).all():
        raise RuntimeError('reference occupation major disagrees')
    joined.to_parquet(priv / 'AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet', index=False)
    os.chmod(priv / 'AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet', 0o600)
    # Aggregate old proxy census in bounded batches. Cache repeated ASTs per batch.
    scopes = ['original_pooled'] + ['major_' + m for m in MAJORS]
    old_totals = {(i, scope): [0., 0.] for i in range(len(specs)) for scope in scopes}
    reader = con.execute('SELECT ' + ','.join(map(qid, sorted(oldcols | {'OCCUPATION_MAJOR', 'arm'}))) + ' FROM parent').fetch_record_batch(65536)
    for batch in reader:
        f = batch.to_pandas(); cache = {}
        def cached(ex):
            key = json.dumps(ex, sort_keys=True)
            if key not in cache:
                cache[key] = expr(f, ex)
            return cache[key]
        old_batch_cache = {}
        masks = {'original_pooled': pd.Series(True, index=f.index)}
        masks.update({'major_' + m: f['OCCUPATION_MAJOR'].astype(str).eq(m) for m in MAJORS})
        for i, spec in enumerate(specs):
            combination = json.dumps([spec['old_domain'], spec['old_outcome']], sort_keys=True)
            if combination not in old_batch_cache:
                od = cached(spec['old_domain']); oy = cached(spec['old_outcome'])
                on = conjunction(od, oy)
                if od.isna().any() or on.isna().any():
                    raise RuntimeError('frozen old proxy contains missing values; define explicit zero auxiliary instead')
                old_batch_cache[combination] = {scope: (int(on[mask].sum()), int(od[mask].sum())) for scope, mask in masks.items()}
            for scope in masks:
                batch_n, batch_d = old_batch_cache[combination][scope]
                old_totals[i, scope][0] += batch_n; old_totals[i, scope][1] += batch_d
    components, rates, discrepancies = [], [], []
    influences = {}
    w = joined['nested_design_weight'].to_numpy(float)
    cells = cell_tuples(joined)
    for i, spec in enumerate(specs):
        rd = expr(joined, spec['reference_domain'])
        ry = expr(joined, spec['measure'])
        od = expr(joined, spec['old_domain']); oy = expr(joined, spec['old_outcome'])
        for scope in scopes:
            mask = pd.Series(True, index=joined.index) if scope == 'original_pooled' else joined['OCCUPATION_MAJOR'].astype(str).eq(scope[6:])
            refdom = conjunction(rd, mask.astype('boolean'))
            nref, dref = known_domain_components(refdom, ry)
            olddom = conjunction(od, mask.astype('boolean')); oldnum = conjunction(olddom, oy)
            popn = sum(N for cell, N in population.items() if scope == 'original_pooled' or cell[0] == scope[6:])
            nt, dt = old_totals[i, scope]
            num = estimate_component(nref, oldnum, w, nt, popn)
            den = estimate_component(dref, olddom, w, dt, popn)
            point, status = corrected_point(num, den)
            label = {k: spec[k] for k in ('question', 'domain', 'eligibility', 'measure', 'proxy_kind', 'old_comparator_available')}
            label['scope'] = scope
            envelope = ht_envelope(refdom, ry, w)
            influence = None; se = None
            if point is not None and a.enable_design_se:
                residual = (nref.to_numpy(float) - oldnum.to_numpy(float)) - point * (dref.to_numpy(float) - olddom.to_numpy(float))
                influence = residual / den['corrected_total_point']
                variance = design_variance(influence, cells, population)
                se = float(np.sqrt(variance)) if variance is not None else None
            key = tuple(label[k] for k in ('question', 'domain', 'eligibility', 'measure', 'scope'))
            if influence is not None:
                influences[key] = influence
            rates.append({**label, 'point': point, 'design_se': se, 'status': status,
                'corrected_numerator_raw': num['corrected_total_point'], 'corrected_denominator_raw': den['corrected_total_point'],
                'reference_known_domain_sample_ads': int(dref.sum()), 'reference_known_positive_sample_ads': int(nref.sum()),
                'old_proxy_rate': nt / dt if dt > 0 and spec['old_comparator_available'] else None,
                'old_proxy_numerator_raw': nt if spec['old_comparator_available'] else None,
                'old_proxy_denominator_raw': dt if spec['old_comparator_available'] else None, **envelope})
            for component, value in (('numerator', num), ('denominator', den)):
                components.append({**label, 'component': component, **value})
            # Full reference unknowns retained. Error summaries only where an old comparator exists.
            if spec['old_comparator_available']:
                raw_joint = conjunction(refdom, ry)
                discrepancy = estimate_component(raw_joint, oldnum, w, nt, popn)
                discrepancies.append({**label, **discrepancy})
    # Equal .25 across the four predeclared majors, including covariance from the same sample.
    groups = {}
    for row in rates:
        if row['scope'].startswith('major_'):
            key = tuple(row[k] for k in ('question', 'domain', 'eligibility', 'measure'))
            groups.setdefault(key, {})[row['scope'][6:]] = row
    for key, parts in groups.items():
        row = {k: v for k, v in parts[MAJORS[0]].items() if k in ('question', 'domain', 'eligibility', 'measure', 'proxy_kind', 'old_comparator_available')}
        row['scope'] = 'equal_0.25_major_standardization'
        fields = ('point', 'full_target_unknown_lower', 'full_target_unknown_upper', 'old_proxy_rate')
        for field in fields:
            row[field] = sum(parts[m][field] for m in MAJORS) / 4 if all(m in parts and parts[m][field] is not None for m in MAJORS) else None
        row['status'] = 'reference_known_domain_only' if row['point'] is not None else 'missing_required_major_no_renormalization'
        keys = [(*key, 'major_' + m) for m in MAJORS]
        row['design_se'] = None
        if all(k in influences for k in keys):
            influence = sum(influences[k] for k in keys) / 4
            influences[(*key, row['scope'])] = influence
            variance = design_variance(influence, cells, population)
            row['design_se'] = float(np.sqrt(variance)) if variance is not None else None
        rates.append(row)
    contrasts = []
    rates_lookup = {tuple(r[k] for k in ('question', 'domain', 'eligibility', 'measure', 'scope')): r for r in rates}
    for key, left in rates_lookup.items():
        question, domain, eligibility, measure, scope = key
        if domain != GA:
            continue
        bkey = (question, GB, eligibility, measure, scope)
        right = rates_lookup[bkey]
        lower = left['full_target_unknown_lower'] - right['full_target_unknown_upper'] if left['full_target_unknown_lower'] is not None and right['full_target_unknown_upper'] is not None else None
        upper = left['full_target_unknown_upper'] - right['full_target_unknown_lower'] if left['full_target_unknown_upper'] is not None and right['full_target_unknown_lower'] is not None else None
        se = None
        if key in influences and bkey in influences:
            variance = design_variance(influences[key] - influences[bkey], cells, population)
            se = float(np.sqrt(variance)) if variance is not None else None
        contrasts.append(dict(question=question, eligibility=eligibility, measure=measure, scope=scope,
            contrast='GenAI_minus_traditional_software', point=left['point'] - right['point'] if left['point'] is not None and right['point'] is not None else None,
            design_se=se, full_target_unknown_lower=lower, full_target_unknown_upper=upper))
    files = {'CORRECTED_DOMAIN_PROPORTIONS.csv': rates, 'CORRECTED_CONTRASTS.csv': contrasts,
             'CORRECTED_COMPONENT_TOTALS.csv': components, 'OLD_NEW_DISCREPANCIES.csv': discrepancies}
    for name, rows in files.items():
        pd.DataFrame(rows).to_csv(out / name, index=False)
    transition = joined[['arm', 'technology_group', 'nested_design_weight']].copy()
    transition['technology_group'] = transition['technology_group'].fillna('unknown_reference_membership')
    transition.groupby(['arm', 'technology_group'], dropna=False).agg(sample_ads=('arm', 'size'), design_weight_mass=('nested_design_weight', 'sum')).reset_index().to_csv(out / 'OLD_NEW_TECHNOLOGY_TRANSITION.csv', index=False)
    status_cols = [x for x in joined if x.startswith('status_')]
    status_rows = []
    for name in status_cols:
        for st, count in joined[name].value_counts(dropna=False).items():
            status_rows.append(dict(family=name[7:], status=st, ads=int(count), design_weight_mass=float(joined.loc[joined[name].eq(st), 'nested_design_weight'].sum())))
    pd.DataFrame(status_rows).to_csv(out / 'REFERENCE_FAMILY_STATUS_COUNTS.csv', index=False)
    receipt = dict(version=VERSION, status='pass', created_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256={p.name: sha(p) for p in Path(__file__).parent.glob('*.py')},
        input_sha256={'fixed': sha(a.fixed), 'reference': sha(a.reference), 'allocation': sha(a.allocation), 'reference_receipt': sha(a.reference_receipt), 'isolation_register': sha(a.isolation_register),
            'parent_files': [{'ordinal': i, 'sha256': sha(p), 'bytes': Path(p).stat().st_size} for i, p in enumerate(paths)],
            'spec': sha(a.spec) if a.spec else None},
        output_sha256={name: sha(out / name) for name in [*files, 'REFERENCE_FAMILY_STATUS_COUNTS.csv', 'OLD_207_CELL_CENSUS.csv', 'OLD_NEW_TECHNOLOGY_TRANSITION.csv']},
        private_bridge={'rows': len(joined), 'sha256': sha(priv / 'AD_LEVEL_DESIGN_BRIDGE_PRIVATE.parquet')},
        checks={'sample_ads': 10000, 'exposed_ads_preserved': 718, 'isolated_contexts_preserved': 14, 'isolated_ads_preserved': int(isolated_ads.sum()), 'parent_ads': 1157573, 'arm_cells': 207,
            'parent_cell_census_matches': True, 'canonical_bridge_unique': True, 'dedicated_probability_reciprocity': True,
            'formal800_w3_used': False, 'no_body_or_quote_columns_read': True},
        assumptions={'variance': 'stratified SRSWOR conditional on treating independent salted MD5 orderings as exchangeable draws; all sample rows and 207 cells enter residual variance',
            'enabled_design_se': a.enable_design_se, 'unknowns': 'main known-reference-domain ratio; separate nonnegative HT unknown/membership envelopes, no MAR imputation',
            'unsupported_old': 'explicit zero auxiliary yields HT reference mass; raw old missing retained and no comparator/error-rate claim',
            'invalid_totals': 'raw retained; rate unavailable; no clipping',
            'standardization': 'four fixed SOC majors 11/13/15/17 at .25 each; no missing-cell renormalization',
            'target': 'original 69-cell technology-screened candidate parent frame; neither all jobs nor causal comparison'},
        runtime={'python': platform.python_version(), 'pandas': pd.__version__, 'numpy': np.__version__, 'duckdb': duckdb.__version__})
    (out / 'RUN_RECEIPT_PUBLIC.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    con.close()
    print(json.dumps({'status': 'pass', 'rows': len(rates), 'contrasts': len(contrasts), 'parent_ads': 1157573}))


if __name__ == '__main__':
    main()
