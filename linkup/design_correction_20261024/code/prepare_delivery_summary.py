#!/usr/bin/env python3
"""Prepare a compact delivery using aggregate CSV/JSON results only.

Run in a scheduled cloud job after the accepted correction calculation. This
helper never opens private input data, row-level keys, text, or semantic labels.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

GA = 'genai_use_with_or_without_software'
GB = 'traditional_software_use_no_ai'
SCOPES = ('original_pooled', 'major_11', 'major_13', 'major_15', 'major_17', 'equal_0.25_major_standardization')
Q1 = tuple('experience_' + x for x in ('general_work', 'occupation_task', 'industry_domain', 'tool_specific'))
Q2 = tuple('duty_' + x for x in ('any', 'independent_judgment', 'client_ownership', 'people_supervision', 'training_mentoring'))
ENTRY = ('graduate_or_noexperience', 'graduate_or_noexperience_unconditional')
VERSION = 'design-correction-aggregate-delivery-v1'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if value is None or isinstance(value, (str, bool)):
        return value
    if hasattr(value, 'item'):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def inference_columns(point, se):
    p, s = number(point), number(se)
    valid_se = s is not None and s >= 0
    ok = p is not None and valid_se
    return dict(point=p, design_se=s if valid_se else None,
        approximate_design_95_lower=p - 1.959963984540054 * s if ok else None,
        approximate_design_95_upper=p + 1.959963984540054 * s if ok else None,
        interval_status='approximate_normal_design_interval_unclipped' if ok else 'no_point' if p is None else 'no_design_se',
        point_available=p is not None, design_se_available=valid_se)


def select_core(rates, contrasts, question, measures, eligibility=None):
    rate_mask = rates['question'].eq(question) & rates['measure'].isin(measures) & rates['scope'].isin(SCOPES)
    if eligibility:
        rate_mask &= rates['eligibility'].isin(eligibility)
    selected = rates.loc[rate_mask]
    lookup = {(r['eligibility'], r['measure'], r['scope'], r['domain']): r for r in selected.to_dict('records')}
    rows = []
    for rec in selected.to_dict('records'):
        rows.append(dict(question=question, row_type='domain_proportion', domain=rec['domain'],
            eligibility=rec['eligibility'], measure=rec['measure'], scope=rec['scope'],
            point_scope='reference_known_domain', original_status=rec.get('status'),
            old_proxy_rate=number(rec.get('old_proxy_rate')),
            old_comparator_status='available_candidate_proxy' if number(rec.get('old_proxy_rate')) is not None else 'no_old_comparator',
            proxy_kind=rec.get('proxy_kind'),
            full_target_unknown_lower=number(rec.get('full_target_unknown_lower')),
            full_target_unknown_upper=number(rec.get('full_target_unknown_upper')),
            unknown_envelope_scope='full_target_nonnegative_HT_reference_mass_envelope_not_CI',
            corrected_numerator_raw=number(rec.get('corrected_numerator_raw')),
            corrected_denominator_raw=number(rec.get('corrected_denominator_raw')),
            reference_known_domain_sample_ads=number(rec.get('reference_known_domain_sample_ads')),
            reference_known_positive_sample_ads=number(rec.get('reference_known_positive_sample_ads')),
            unknown_domain_ads=number(rec.get('unknown_domain_ads')),
            unknown_outcome_in_possible_domain_ads=number(rec.get('unknown_outcome_in_possible_domain_ads')),
            **inference_columns(rec.get('point'), rec.get('design_se'))))
    cmask = contrasts['question'].eq(question) & contrasts['measure'].isin(measures) & contrasts['scope'].isin(SCOPES)
    if eligibility:
        cmask &= contrasts['eligibility'].isin(eligibility)
    for rec in contrasts.loc[cmask].to_dict('records'):
        left = lookup.get((rec['eligibility'], rec['measure'], rec['scope'], GA), {})
        right = lookup.get((rec['eligibility'], rec['measure'], rec['scope'], GB), {})
        old_a, old_b = number(left.get('old_proxy_rate')), number(right.get('old_proxy_rate'))
        old = old_a - old_b if old_a is not None and old_b is not None else None
        rows.append(dict(question=question, row_type='GenAI_minus_software_contrast', domain='GenAI_minus_traditional_software',
            eligibility=rec['eligibility'], measure=rec['measure'], scope=rec['scope'],
            point_scope='difference_between_reference_known_domain_ratios',
            original_status='available' if number(rec.get('point')) is not None else 'no_point',
            old_proxy_rate=old, old_comparator_status='available_candidate_proxy' if old is not None else 'no_old_comparator',
            proxy_kind=left.get('proxy_kind'),
            full_target_unknown_lower=number(rec.get('full_target_unknown_lower')),
            full_target_unknown_upper=number(rec.get('full_target_unknown_upper')),
            unknown_envelope_scope='full_target_nonnegative_HT_reference_mass_contrast_envelope_not_CI',
            **inference_columns(rec.get('point'), rec.get('design_se'))))
    order = {s: i for i, s in enumerate(SCOPES)}
    rows.sort(key=lambda r: (r['eligibility'], r['measure'], order[r['scope']], r['row_type'], r['domain']))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    ap.add_argument('--scheduler-receipt', type=Path, help='optional public scheduler metadata JSON; no private data')
    a = ap.parse_args()
    source = a.results_dir
    required = ('RUN_RECEIPT_PUBLIC.json', 'CORRECTED_DOMAIN_PROPORTIONS.csv', 'CORRECTED_CONTRASTS.csv',
                'REFERENCE_FAMILY_STATUS_COUNTS.csv', 'OLD_NEW_TECHNOLOGY_TRANSITION.csv', 'OLD_207_CELL_CENSUS.csv')
    receipt = json.loads((source / required[0]).read_text())
    if receipt.get('status') != 'pass':
        raise RuntimeError('source calculation receipt is not pass')
    # Bind all aggregates used by this helper to the calculation receipt.
    for name in required[1:]:
        if receipt.get('output_sha256', {}).get(name) != sha(source / name):
            raise RuntimeError('aggregate source hash mismatch: ' + name)
    rates = pd.read_csv(source / 'CORRECTED_DOMAIN_PROPORTIONS.csv')
    contrasts = pd.read_csv(source / 'CORRECTED_CONTRASTS.csv')
    family = pd.read_csv(source / 'REFERENCE_FAMILY_STATUS_COUNTS.csv')
    transitions = pd.read_csv(source / 'OLD_NEW_TECHNOLOGY_TRANSITION.csv')
    census = pd.read_csv(source / 'OLD_207_CELL_CENSUS.csv')
    q1 = select_core(rates, contrasts, 'Q1', Q1)
    q2 = select_core(rates, contrasts, 'Q2', Q2, ENTRY)
    if not q1 or not q2:
        raise RuntimeError('required core comparison selection is empty')
    a.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (('CORE_Q1.csv', q1), ('CORE_Q2.csv', q2)):
        pd.DataFrame(rows).to_csv(a.output_dir / name, index=False)
    known_domain = rates['scope'].eq('original_pooled')
    domain_summary = rates.loc[known_domain, ['question', 'domain', 'eligibility', 'measure', 'reference_known_domain_sample_ads',
        'reference_known_positive_sample_ads', 'unknown_domain_ads', 'unknown_outcome_in_possible_domain_ads',
        'ht_numerator_lower', 'ht_numerator_upper', 'ht_denominator_lower', 'ht_denominator_upper']]
    def statuses(frame, column):
        return {str(k): int(v) for k, v in frame[column].fillna('missing').value_counts(dropna=False).items()}
    all_rows = q1 + q2
    summary = dict(version=VERSION, status='pass', created_utc=datetime.now(timezone.utc).isoformat(),
        calculation_version=receipt.get('version'), source_checks=receipt.get('checks'), assumptions=receipt.get('assumptions'),
        methods_qa={'joint_correction': 'Old proxy census plus dedicated design-weighted reference-minus-proxy residual for both numerator and denominator.',
            'main_scope': 'Operational reference-known domain, including known technology membership, known entry eligibility when applicable, and known outcome. Unknown reference labels remain unmodified.',
            'variance': 'Delta-method ratio residual with all sampled ads in all original arm cells; shared-sample covariance retained in contrasts and equal-major standardization.',
            'hash_assumption': 'Independent salted MD5 orderings are treated as exchangeable SRS draws; this is an explicit design approximation.',
            'invalid_totals': 'Raw corrected totals retained; unavailable rate when denominator is nonpositive or totals outside valid range. No clipping.',
            'unknowns': 'Full-target nonnegative HT reference-mass envelopes are separate sensitivity summaries; they are not confidence intervals or missing-at-random imputations.',
            'normal_interval': 'Point plus or minus 1.959963984540054 design standard errors; approximate, unbounded normal design interval, conditional on stated sampling assumptions.',
            'unsupported_old': 'Explicit zero auxiliary; no old comparator. It is not an observed old negative.',
            'standardization': 'Fixed .25 on each SOC major11,13,15,17; any unavailable required major leaves standardized point unavailable.'},
        counts={'all_domain_rate_rows': len(rates), 'all_contrast_rows': len(contrasts),
            'all_domain_rate_statuses': statuses(rates, 'status'),
            'all_domain_rate_no_point': int(pd.to_numeric(rates['point'], errors='coerce').isna().sum()),
            'all_domain_rate_no_design_se': int(pd.to_numeric(rates['design_se'], errors='coerce').isna().sum()),
            'all_contrast_no_point': int(pd.to_numeric(contrasts['point'], errors='coerce').isna().sum()),
            'all_contrast_no_design_se': int(pd.to_numeric(contrasts['design_se'], errors='coerce').isna().sum()),
            'core_q1_rows': len(q1), 'core_q2_rows': len(q2),
            'core_interval_statuses': dict(Counter(r['interval_status'] for r in all_rows)),
            'parent_census_rows': len(census), 'parent_census_mass': int(census['parent_n'].sum()),
            'transition_sample_ads': int(transitions['sample_ads'].sum()),
            'transition_design_weight_mass': float(transitions['design_weight_mass'].sum())},
        reference_family_status_counts=family.to_dict('records'),
        technology_transitions=transitions.to_dict('records'),
        pooled_measure_unknown_and_mass_accounting=domain_summary.to_dict('records'),
        interpretation_guide=['Compare the old candidate proxy and corrected operational-reference measure only where an old comparator is available.',
            'The main point refers to a reference-known domain. The separate HT envelope concerns unresolved membership/outcomes in the full target.',
            'For a proportion or GenAI-minus-software contrast, use the approximate design interval only under the stated exchangeable-hash sampling assumption.',
            'Do not interpret the unknown envelope as a confidence interval, or the interval as accounting for semantic reference error.',
            'These descriptive comparisons do not identify causal effects, cover all US advertisements, or establish semantic truth.'],
        inputs={name: sha(source / name) for name in required},
        code_sha256=sha(__file__),
        outputs={name: sha(a.output_dir / name) for name in ('CORE_Q1.csv', 'CORE_Q2.csv')},
        scheduler_metadata=json.loads(a.scheduler_receipt.read_text()) if a.scheduler_receipt else None,
        core_q1=q1, core_q2=q2)
    (a.output_dir / 'CORE_COMPARISONS_PUBLIC.json').write_text(json.dumps(clean(summary), indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': 'pass', 'core_q1_rows': len(q1), 'core_q2_rows': len(q2)}))

if __name__ == '__main__':
    main()
