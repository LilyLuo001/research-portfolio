"""Repeated synthetic NULL experiments, not empirical power or P1 evidence.

Event clusters are independent by construction here. This does not validate
issuer/date multiway clustering or a real dependence graph.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from synthetic_checks import fieller

SEED = 20260922
REPLICATIONS = 500


def run():
    rng = np.random.default_rng(SEED)
    rejection_iid = rejection_cluster = 0
    unbounded_weak = unbounded_strong = 0
    ratio_covered_weak = ratio_covered_strong = 0
    # Fixed illustrative critical value, approximately two-sided t(.975,79).
    # Not an estimated or adaptive threshold.
    critical = 1.990
    events, duplicates = 80, 8
    for _ in range(REPLICATIONS):
        z = rng.normal(size=events)
        x = np.repeat(z, duplicates)
        # Null slope, but multiple ETFs inherit the same event-level disturbance.
        y = np.repeat(rng.normal(size=events), duplicates) + rng.normal(scale=.2, size=len(x))
        design = np.column_stack([np.ones(len(x)), x])
        inv = np.linalg.inv(design.T@design)
        beta = inv@design.T@y
        residual = y-design@beta
        influence = (design@inv)[:,1]*residual
        var_iid = np.sum(influence**2)*len(x)/(len(x)-2)
        group_scores = influence.reshape(events, duplicates).sum(axis=1)
        var_cluster = (group_scores@group_scores)*events/(events-1)*(len(x)-1)/(len(x)-2)
        rejection_iid += abs(beta[1])/np.sqrt(var_iid) > critical
        rejection_cluster += abs(beta[1])/np.sqrt(var_cluster) > critical

        # Known Gaussian covariance isolates Fieller algebra/coverage from estimation.
        cov = np.diag([.01, .01])
        for denominator, label in [(1., 'strong'), (.01, 'weak')]:
            true_ratio = .5
            n, d = rng.multivariate_normal([denominator*true_ratio, denominator], cov)
            region = fieller(n, d, cov, critical=1.96)
            covered = (n-true_ratio*d)**2 <= 1.96**2*(cov[0,0]+true_ratio**2*cov[1,1])
            if label == 'weak':
                unbounded_weak += region['kind'] in {'ALL_REAL','TWO_UNBOUNDED_RAYS','HALF_LINE'}
                ratio_covered_weak += covered
            else:
                unbounded_strong += region['kind'] in {'ALL_REAL','TWO_UNBOUNDED_RAYS','HALF_LINE'}
                ratio_covered_strong += covered
    rate = lambda n: float(n/REPLICATIONS)
    summary = {
        'status': 'SYNTHETIC_NULL_CALIBRATION_ONLY', 'seed': SEED,
        'replications': REPLICATIONS,
        'design': {'independent_events': events, 'ETF_rows_per_event': duplicates,
                   'true_event_response_difference_slope': 0, 'critical_value': critical},
        'false_rejection_rate_IID_rows': rate(rejection_iid),
        'false_rejection_rate_event_cluster': rate(rejection_cluster),
        'weak_denominator_ratio_coverage': rate(ratio_covered_weak),
        'strong_denominator_ratio_coverage': rate(ratio_covered_strong),
        'weak_denominator_unbounded_set_rate': rate(unbounded_weak),
        'strong_denominator_unbounded_set_rate': rate(unbounded_strong),
        'MC_standard_error_near_nominal_5pct': float(np.sqrt(.05*.95/REPLICATIONS)),
        'limits': ['Not P1 power or sample feasibility',
                   'No empirical inputs; independent event clusters are assumed',
                   'No real issuer/date multiway inference certification',
                   'Fieller uses known Gaussian covariance in this experiment',
                   'No seed search or tuning to obtain a pass'],
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'fieller_source_sha256': hashlib.sha256(Path(__file__).with_name('synthetic_checks.py').read_bytes()).hexdigest()
    }
    Path(__file__).with_name('INFERENCE_STRESS_RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    run()
