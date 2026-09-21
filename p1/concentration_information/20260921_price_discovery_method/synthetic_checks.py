"""Synthetic algebra/estimator checks only. No empirical data or network access.

Not a power calculation, not an implementation of a production cluster inference
procedure, and not a test of whether P1's economic hypothesis is true.
"""
import hashlib
import json
from pathlib import Path
import numpy as np

SEED = 20260921


def fieller(n, d, covariance, critical=1.96):
    """Solve (n-r*d)^2 <= c^2 Var(n-r*d); retain unbounded sets."""
    c2 = critical ** 2
    a = d*d - c2*covariance[1, 1]
    b = -2*n*d + 2*c2*covariance[0, 1]
    c = n*n - c2*covariance[0, 0]
    disc = b*b - 4*a*c
    if abs(a) < 1e-14:
        if abs(b) < 1e-14:
            return {"kind": "ALL_REAL" if c <= 0 else "EMPTY"}
        return {"kind": "HALF_LINE", "boundary": float(-c/b),
                "direction": "LE" if b > 0 else "GE"}
    if disc < 0:
        return {"kind": "ALL_REAL" if a < 0 else "EMPTY"}
    roots = sorted([(-b-np.sqrt(disc))/(2*a), (-b+np.sqrt(disc))/(2*a)])
    return {"kind": "BOUNDED" if a > 0 else "TWO_UNBOUNDED_RAYS",
            "boundaries": [float(v) for v in roots]}


def fit(x, responses):
    """Joint intercept/slope OLS; IID HC0 covariance, for toy fixtures only."""
    design = np.column_stack([np.ones(len(x)), x])
    inverse = np.linalg.inv(design.T @ design)
    coef = inverse @ design.T @ responses
    residual = responses-design@coef
    influence = ((design@inverse)[:, 1, None])*residual
    covariance = influence.T @ influence
    slopes = coef[1]
    # Columns: ETF early, basket early, ETF terminal, basket terminal.
    transform = np.array([[1., -1., 0., 0.], [0., 0., .5, .5]])
    n, d = transform@slopes
    cov = transform@covariance@transform.T
    interval = fieller(n, d, cov)
    out = {"slopes": slopes.tolist(), "early_difference": float(n),
           "terminal_response": float(d), "ratio_set": interval,
           "ratio_point": float(n/d) if abs(d) > 1e-12 else None,
           "interval_assumption": "IID_HC0_NORMAL_APPROXIMATION_SYNTHETIC_ONLY"}
    return out


def make_case(a_e, a_b, weight=.1, noise_e=.02, noise_b=.02,
              terminal=1., n=12000, seed=SEED):
    rng = np.random.default_rng(seed)
    z = rng.normal(size=n)
    x = weight*z
    eps = rng.normal(size=(n, 4))
    y = x[:, None]*np.array([a_e, a_b, terminal, terminal])
    y += eps*np.array([noise_e, noise_b, .01, .01])
    return fit(x, y)


def decomposition(p0, p1, d0, d1):
    p0, p1, d0, d1 = map(np.asarray, (p0, p1, d0, d1))
    within = np.dot((p1+p0)/2, d1-d0)
    composition = np.dot((d1+d0)/2, p1-p0)
    return {"total_change": float(p1@d1-p0@d0),
            "within_response_change": float(within),
            "composition_change": float(composition)}


def main():
    checks = []
    def check(name, condition, details):
        checks.append({"name": name, "passed": bool(condition), "details": details})

    null = make_case(.6, .6, noise_e=.005, noise_b=.06)
    bounds = null['ratio_set'].get('boundaries', [])
    check("equal_news_response_unequal_noise", len(bounds)==2 and bounds[0] <= 0 <= bounds[1], null)

    low = make_case(.8, .4, weight=.03, noise_e=0., noise_b=0.)
    high = make_case(.8, .4, weight=.3, noise_e=0., noise_b=0.)
    check("weight_rescaling_does_not_create_speed_change",
          abs(low['ratio_point']-high['ratio_point']) < .003, {"low": low, "high": high})

    # Constant response laws, changing portfolio composition: no within change.
    mech = decomposition([.2,.8], [.6,.4], [.6,.1], [.6,.1])
    check("composition_only_is_not_mechanism_change",
          abs(mech['within_response_change']) < 1e-12 and abs(mech['total_change']-.2)<1e-12, mech)
    hetero = decomposition([.2,.8], [.6,.4], [.2,.1], [.6,.1])
    check("true_top_only_change_remains_separate_from_composition",
          abs(hetero['total_change']-hetero['within_response_change']-hetero['composition_change'])<1e-12
          and hetero['within_response_change']>0, hetero)

    e_leads, b_leads = make_case(.8,.3), make_case(.3,.8)
    check("both_directions_recoverable", e_leads['ratio_point']>.4 and b_leads['ratio_point']<-.4,
          {"ETF_first": e_leads, "basket_first": b_leads})

    weak = fieller(.05, 0., np.diag([.01,.01]))
    check("zero_terminal_signal_not_forced_into_finite_ratio", weak['kind']!='BOUNDED', weak)

    over = make_case(1.8,.9)
    # Positive early difference is not the same as being closer to terminal.
    e, b, e_H, b_H = over['slopes']
    check("overshoot_can_fake_leadership", over['ratio_point']>0 and abs(e-e_H)>abs(b-b_H), over)

    e_bid, e_ask, b_bid, b_ask = .9, 1.1, .0, 1.1
    midpoint_gap = (e_bid+e_ask-b_bid-b_ask)/2
    check("midpoint_lead_can_reflect_slow_opposite_quote_side",
          midpoint_gap>0 and e_ask-b_ask==0.,
          {"midpoint_gap": midpoint_gap, "ask_gap": e_ask-b_ask,
           "interpretation": "MIDQUOTE_ONLY_LEADERSHIP_NOT_CERTIFIED"})

    # Two structural stories, exactly the same observable series: an impossibility fixture.
    rng = np.random.default_rng(SEED)
    news = rng.normal(size=100)
    e_path = news.copy()
    b_relay = np.r_[0., e_path[:-1]]
    b_common_news_delayed = np.r_[0., news[:-1]]
    check("relay_and_common_news_delay_observational_equivalence",
          np.array_equal(b_relay, b_common_news_delayed),
          {"max_observable_difference": float(np.max(abs(b_relay-b_common_news_delayed))),
           "causal_route": "NOT_IDENTIFIED_FROM_THESE_PRICES"})

    check("timestamp_uncertainty_blocks_fine_ordering", not (1. > 2.*2.),
          {"apparent_gap_seconds": 1, "each_timestamp_uncertainty_seconds": 2,
           "ordering": "UNRESOLVED"})

    # Current quote state is carried until an update/cancellation, not until next trade.
    valid_quote, changed = True, False
    check("unchanged_live_quote_is_not_missing", valid_quote and not changed,
          {"valid_live_state": valid_quote, "quote_changed": changed,
           "scope": "logical_fixture_not_feed_parser_validation"})

    result = {"status": "SYNTHETIC_FIXTURES_ONLY", "seed": SEED,
              "numpy_version": np.__version__, "checks": checks,
              "passed": sum(c['passed'] for c in checks), "total": len(checks),
              "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "empirical_data_read": False, "empirical_power": "NOT_RUN",
              "production_inference": "NOT_IMPLEMENTED_OR_CERTIFIED"}
    output = Path(__file__).with_name('SYNTHETIC_RESULTS.json')
    output.write_text(json.dumps(result, indent=2)+"\n", encoding='utf-8')
    print(json.dumps({"passed": result['passed'], "total": result['total'], "output": str(output)}))
    if not all(c['passed'] for c in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
