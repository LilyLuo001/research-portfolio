"""No empirical observations: synthetic-only implementation tests."""
import hashlib
import json
from pathlib import Path
import numpy as np
from design_engine import fit_wave, unique_event_covariance

OUT = Path(__file__).resolve().parent


def sample():
    rows = []
    y = []
    for stock in range(8):
        group = 'H' if stock % 2 else 'L'
        industry = str(stock // 4)
        for quarter in range(4):
            post = int(quarter >= 2)
            for k, sue in enumerate((-1.5, -.5, .5, 1.5)):
                rows.append(dict(wave='SYNTH_W', event_id=f'E{stock}_{quarter}_{k}', stock=str(stock), industry=industry, cell=f'Q{quarter}', group=group, post=post, sue=sue))
                base = 1 + .2*stock + .1*quarter
                slope = .3*stock + .2*quarter + .4*post + (2*post if group == 'H' else 0)
                # Orthogonal nonlinear term supplies residual variation without changing the linear coefficient.
                noise = .02*(sue*sue - 1.25)
                y.append([base + slope*sue + noise, 3*base + 2*slope*sue + .5*noise])
    return rows, np.array(y)


def expect_error(rows, y, prefix):
    try:
        fit_wave(rows, y)
    except ValueError as error:
        assert str(error).startswith(prefix), str(error)
        return True
    raise AssertionError(f'Expected {prefix}')


def quarterly_sample():
    """One synthetic earnings observation per stock-quarter; no daily panel."""
    rng = np.random.default_rng(1515)
    rows, outcomes = [], []
    for stock in range(8):
        high = bool(stock % 2)
        for quarter in range(12):
            post = int(quarter >= 8)
            sue = float(rng.normal())
            rows.append(dict(wave='QUARTERLY_SYNTH', event_id=f'QE{stock}_{quarter}', stock=str(stock), group='H' if high else 'L', industry=str(stock // 4), cell=f'Q{quarter}', post=post, sue=sue))
            outcomes.append(.2*stock + .1*quarter + (.3*stock + .15*quarter + 1.25*high*post)*sue)
    return rows, np.asarray(outcomes)


def main():
    rows, y = sample()
    fit = fit_wave(rows, y)
    tests = {}
    assert np.allclose(fit.contrast, [2., 4.], atol=1e-10)
    tests['known_two_horizon_slope_DID'] = True
    assert fit.rank < fit.columns and fit.contrast_rowspace_residual < 1e-9
    tests['exact_nuisance_redundancy_does_not_invalidate_identified_contrast'] = True
    # Delete all events for one positive-weight stock-calendar cell.
    keep = [i for i, r in enumerate(rows) if not (r['stock'] == '0' and r['cell'] == 'Q0')]
    tests['missing_required_observed_stock_cell_fails_closed'] = expect_error([rows[i] for i in keep], y[keep], 'MISSING_REQUIRED_STOCK_CELL')
    keep = [i for i, r in enumerate(rows) if not (r['group'] == 'L' and r['post'] == 1)]
    tests['absent_low_POST_group_fails_closed'] = expect_error([rows[i] for i in keep], y[keep], 'NO_COMMON_CALENDAR_CELLS')
    tests['duplicate_within_wave_not_new_information'] = expect_error(rows + [rows[0]], np.vstack([y, y[0]]), 'DUPLICATE_ECONOMIC_EVENT')
    zero_sue = [dict(r, sue=0.) for r in rows]
    tests['zero_SUE_variation_blocks_contrast'] = expect_error(zero_sue, y, 'REQUIRED_CONTRAST_NOT_IDENTIFIED')
    base, n = unique_event_covariance([fit], [1.])
    duplicated, n2 = unique_event_covariance([fit, fit], [.5, .5])
    assert n == n2 == len(rows) and np.allclose(base, duplicated, rtol=1e-12, atol=1e-14)
    tests['duplicate_stacks_joint_event_scores_do_not_gain_precision'] = True
    assert abs(base[0, 1]) > 1e-12
    tests['cross_horizon_covariance_retained'] = True
    # Permuting input order cannot alter standardization or estimates.
    order = np.random.default_rng(20260915).permutation(len(rows))
    perm = fit_wave([rows[i] for i in order], y[order])
    assert np.allclose(perm.contrast, fit.contrast, atol=1e-10)
    tests['row_order_invariant'] = True
    shared_calendar = [dict(r, cell='Q_SHARED') for r in rows]
    shared = fit_wave(shared_calendar, y)
    assert np.allclose(shared.contrast, fit.contrast, atol=1e-10)
    tests['calendar_cell_can_appear_in_both_regimes'] = True
    qrows, qy = quarterly_sample()
    qfit = fit_wave(qrows, qy)
    assert np.allclose(qfit.contrast, [1.25], atol=1e-9)
    tests['one_event_per_stock_quarter_synthetic_truth_recovered'] = True
    receipt = {
        'status': 'SYNTHETIC_INTERFACE_TESTS_PASS_NOT_RESEARCH_PILOT_PASS',
        'synthetic_rows': len(rows), 'synthetic_columns': fit.columns, 'synthetic_rank': fit.rank,
        'quarterly_fixture': {'rows': len(qrows), 'columns': qfit.columns, 'rank': qfit.rank, 'PRE_quarters': 8, 'POST_quarters': 4, 'known_contrast_recovered': True},
        'tests': tests, 'test_count': len(tests),
        'source_data_opened': False, 'empirical_power': False,
        'actual_POST_values': False, 'inference_validated': False,
        'limitations': ['Stock-industry identity fixed in fixture; changing classification requires explicit policy', 'Event-score covariance primitive omits sponsor/date/serial dependence; not an inference estimator', 'Synthetic multiple events per stock-quarter are artificial for interface tests, not a proposed earnings panel', 'No numeric rank of real PRE or POST sample is established'],
        'code_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'design_engine.py', OUT/'test_design_engine.py')},
    }
    (OUT/'SYNTHETIC_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
