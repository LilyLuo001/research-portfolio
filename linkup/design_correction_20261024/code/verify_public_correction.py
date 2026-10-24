#!/usr/bin/env python3
"""Independent aggregate arithmetic/scope gate. Reads public outputs only.

Does not re-estimate sampling variance or validate semantic reference accuracy.
Unknown envelopes are HT missingness sensitivity summaries, not confidence limits.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MAJORS = ('11', '13', '15', '17')
GA = 'genai_use_with_or_without_software'
GB = 'traditional_software_use_no_ai'
KEY = ('question', 'domain', 'eligibility', 'measure', 'scope')


def number(row, name):
    value = row.get(name, '')
    return None if value in ('', None) else float(value)


def close(a, b):
    return a is None and b is None or (a is not None and b is not None and
        math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-7))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--public-output', required=True)
    ap.add_argument('--qa-output', help='defaults to public-output/QA_PUBLIC.json')
    a = ap.parse_args()
    folder = Path(a.public_output)
    issues, counts = Counter(), Counter()

    def check(condition, name):
        counts['assertions'] += 1
        if not condition:
            issues[name] += 1

    def rows(name):
        with (folder / name).open(newline='') as handle:
            result = list(csv.DictReader(handle))
        counts[name + '_rows'] = len(result)
        return result

    receipt_path = folder / 'RUN_RECEIPT_PUBLIC.json'
    receipt = json.loads(receipt_path.read_text())
    check(receipt.get('status') == 'pass', 'run_status')
    for name, expected in {'sample_ads': 10000, 'parent_ads': 1157573,
            'arm_cells': 207, 'exposed_ads_preserved': 718,
            'isolated_contexts_preserved': 14, 'isolated_ads_preserved': 16}.items():
        check(receipt.get('checks', {}).get(name) == expected, 'receipt_' + name)
    check(receipt.get('private_bridge', {}).get('rows') == 10000, 'receipt_bridge_rows')
    check(receipt.get('checks', {}).get('formal800_w3_used') is False, 'formal800_weights')
    hashes = receipt.get('output_sha256', {})
    required = {'CORRECTED_COMPONENT_TOTALS.csv', 'CORRECTED_DOMAIN_PROPORTIONS.csv',
        'CORRECTED_CONTRASTS.csv', 'OLD_NEW_DISCREPANCIES.csv', 'OLD_207_CELL_CENSUS.csv',
        'OLD_NEW_TECHNOLOGY_TRANSITION.csv', 'REFERENCE_FAMILY_STATUS_COUNTS.csv'}
    check(required.issubset(hashes), 'required_output_hashes')
    for name, expected in hashes.items():
        path = folder / name
        check(path.is_file() and digest(path) == expected, 'public_output_hash')
    census = rows('OLD_207_CELL_CENSUS.csv')
    check(len(census) == 207, 'census_cell_count')
    check(len({tuple(r[k] for k in ('OCCUPATION_MAJOR', 'CENSUS_REGION', 'created_year', 'arm'))
        for r in census}) == 207, 'census_unique_cells')
    for arm, N in {'A': 10075, 'B': 1064428, 'C': 83070}.items():
        check(close(sum(number(r, 'parent_n') for r in census if r['arm'] == arm), N), 'census_parent_' + arm)
        check(sum(r['arm'] == arm for r in census) == 69, 'census_cells_' + arm)

    components = rows('CORRECTED_COMPONENT_TOTALS.csv')
    discrepancies = rows('OLD_NEW_DISCREPANCIES.csv')
    for row in components + discrepancies:
        lower = number(row, 'old_census_total') - number(row, 'old_sample_ht_total') + number(row, 'reference_known_positive_ht_total')
        unknown = number(row, 'reference_unknown_ht_mass')
        check(close(number(row, 'corrected_total_lower_raw'), lower), 'component_lower_identity')
        check(close(number(row, 'corrected_total_upper_raw'), lower + unknown), 'component_upper_identity')
        check(unknown >= 0, 'negative_unknown_mass')
        expected_point = lower if number(row, 'reference_unknown_ads') == 0 else None
        check(close(number(row, 'corrected_total_point'), expected_point), 'component_point_missingness')
        check(number(row, 'reference_known_ads') + number(row, 'reference_unknown_ads') == 10000, 'component_all_sample_rows')
        counts['negative_raw_component_totals'] += int(lower < 0)
        if row.get('proxy_kind') == 'zero_auxiliary_no_old_comparator':
            # Unavailable old OUTCOME means zero numerator auxiliary. Q1 still
            # uses the observed old A/B group indicator for its denominator;
            # Q2 has no old domain auxiliary and therefore zeroes both.
            if row.get('component') == 'denominator' and row['question'] == 'Q1':
                old_arm = {GA: 'A', GB: 'B'}.get(row['domain'])
                expected = sum(number(r, 'parent_n') for r in census
                    if r['arm'] == old_arm and (row['scope'] == 'original_pooled'
                    or r['OCCUPATION_MAJOR'] == (row['scope'][6:] if row['scope'].startswith('major_') else row['scope'])))
                check(old_arm is not None and close(number(row, 'old_census_total'), expected)
                    and close(number(row, 'old_sample_ht_total'), expected), 'q1_old_domain_calibration')
            else:
                check(close(number(row, 'old_census_total'), 0) and close(number(row, 'old_sample_ht_total'), 0), 'zero_auxiliary')
    component_map = {tuple(r[k] for k in KEY) + (r['component'],): r for r in components}
    check(len(component_map) == len(components), 'duplicate_components')
    rates = rows('CORRECTED_DOMAIN_PROPORTIONS.csv')
    rate_map = {tuple(r[k] for k in KEY): r for r in rates}
    check(len(rate_map) == len(rates), 'duplicate_rates')
    enabled = receipt.get('assumptions', {}).get('enabled_design_se') is True
    for row in rates:
        key = tuple(row[k] for k in KEY)
        point, se = number(row, 'point'), number(row, 'design_se')
        check(se is None or math.isfinite(se) and se >= 0, 'invalid_rate_se')
        counts['valid_points_missing_se'] += int(point is not None and se is None)
        check(not enabled or point is None or se is not None, 'enabled_valid_point_missing_se')
        check(point is not None or se is None, 'se_without_rate')
        lo, hi = number(row, 'full_target_unknown_lower'), number(row, 'full_target_unknown_upper')
        check(lo is None and hi is None or lo is not None and hi is not None and 0 <= lo <= hi <= 1, 'invalid_ht_envelope')
        if row['scope'] == 'equal_0.25_major_standardization':
            parts = [rate_map.get(key[:-1] + ('major_' + m,)) for m in MAJORS]
            check(all(p is not None for p in parts), 'missing_required_major_row')
            for field in ('point', 'full_target_unknown_lower', 'full_target_unknown_upper', 'old_proxy_rate'):
                values = [number(p, field) if p is not None else None for p in parts]
                expected = sum(values) / 4 if all(v is not None for v in values) else None
                check(close(number(row, field), expected), 'major_quarter_' + field)
            check(row['status'] == ('reference_known_domain_only' if point is not None else 'missing_required_major_no_renormalization'), 'standardized_status')
            continue
        num = component_map.get(key + ('numerator',))
        den = component_map.get(key + ('denominator',))
        check(num is not None and den is not None, 'missing_rate_components')
        if num is None or den is None:
            continue
        n, d = number(num, 'corrected_total_point'), number(den, 'corrected_total_point')
        check(close(number(row, 'corrected_numerator_raw'), n) and close(number(row, 'corrected_denominator_raw'), d), 'raw_component_preservation')
        valid = n is not None and d is not None and d > 0 and 0 <= n <= d <= number(den, 'population_n')
        check(close(point, n / d if valid else None), 'rate_corrected_ratio')
        check(row['status'] == ('reference_known_domain_only' if valid else 'unavailable_invalid_corrected_totals'), 'rate_status')
        if row.get('old_comparator_available') == 'False':
            check(all(number(row, x) is None for x in ('old_proxy_rate', 'old_proxy_numerator_raw', 'old_proxy_denominator_raw')), 'unavailable_old_comparator')
    contrasts = rows('CORRECTED_CONTRASTS.csv')
    for row in contrasts:
        base = (row['question'], GA, row['eligibility'], row['measure'], row['scope'])
        left = rate_map.get(base)
        right = rate_map.get((base[0], GB, *base[2:]))
        check(left is not None and right is not None, 'missing_contrast_rates')
        if left is None or right is None:
            continue
        for field, lf, rf in [('point', 'point', 'point'),
                ('full_target_unknown_lower', 'full_target_unknown_lower', 'full_target_unknown_upper'),
                ('full_target_unknown_upper', 'full_target_unknown_upper', 'full_target_unknown_lower')]:
            x, y = number(left, lf), number(right, rf)
            check(close(number(row, field), x - y if x is not None and y is not None else None), 'contrast_' + field)
        se = number(row, 'design_se')
        check(se is None or math.isfinite(se) and se >= 0, 'invalid_contrast_se')
        check(not enabled or number(row, 'point') is None or se is not None, 'enabled_contrast_missing_se')
        check(number(row, 'point') is not None or se is None, 'se_without_contrast')
    transition = rows('OLD_NEW_TECHNOLOGY_TRANSITION.csv')
    check(close(sum(number(r, 'sample_ads') for r in transition), 10000), 'transition_sample_total')
    check(close(sum(number(r, 'design_weight_mass') for r in transition), 1157573), 'transition_parent_weight_total')
    result = {'status': 'pass' if not issues else 'fail',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Public aggregate arithmetic, output hashes and receipt scope only; no semantic gold claim or independent variance recomputation.',
        'run_receipt_sha256': digest(receipt_path), 'qa_code_sha256': digest(Path(__file__)),
        'counts': dict(counts), 'issues': dict(issues),
        'limitations': ['SE checks cover availability and nonnegativity only; row-level residual variance is covered by separate static design QA.',
            'No sample-cell n or singleton counts are published here; no singleton claims are inferred from parent-cell census.',
            'HT unknown envelopes are missingness sensitivity summaries, not confidence intervals.']}
    destination = Path(a.qa_output) if a.qa_output else folder / 'QA_PUBLIC.json'
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'issues': dict(issues), 'assertions': counts['assertions']}))
    return 0 if not issues else 1


if __name__ == '__main__':
    raise SystemExit(main())
