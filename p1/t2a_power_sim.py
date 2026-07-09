"""P1-T2a — simulated power analysis / kill-switch pre-flight (AMEND P1-2).

No WRDS access. Inputs: p1/events_from_note.csv (public per-fund AUM with
source locators) + coarse priors, every one labeled PRIOR-n below. Outcome is
measured in sigma units of the stock-level pre/post change in a standardized
earnings-information-incorporation measure (FERC/PEAD residual style), so no
literature effect-size numbers are needed for the MDE table itself; mapping
MDE to literature magnitudes is CITE_REQUEST (no literature pack in repo).

Design mirrors P1's main spec: one anchor wave (2021-06), stacked DiD via
shared.econlib.did.stacked_did, window (-4,+4) quarters.

PRIORS (all coarse, all flagged in power_memo.md):
  PRIOR-1  US equity universe ~3,000 investable names; cap distribution
           log-normal(mu=ln(2e9), sigma=1.6) truncated to [$50m, $3T] —
           scale anchor only; results reported in relative terms.
  PRIOR-2  fund style universes by cap rank: DFUS large-cap (top 1000),
           DFAC all-cap (top 2500), DFAS small-cap (rank 1000-3000),
           DFAT small/mid value (rank 800-2800).
  PRIOR-3  within-universe weights w_if ∝ cap_i^gamma * jitter, jitter
           lognormal(0, 0.5) (DFA runs tilted quasi-active portfolios, not
           exact cap-weights). dose_i = sum_f AUM_f * w_if / mktcap_i.
           gamma is the scenario dial — smaller gamma tilts weight toward
           smaller names, concentrating dose where it is detectable:
             optimistic  gamma=0.70 (strong small/value tilt)
             base        gamma=0.85
             pessimistic gamma=1.00 (pure cap-weight => flattest dose)
  PRIOR-4  materiality threshold theta: a stock is 'treated' when total
           conversion dose >= 25bps of market cap (sensitivity: 10/50bps).
  PRIOR-5  outcome noise iid N(0,1) across stock-quarters. This is the
           OPTIMISTIC noise model (no serial correlation, no common shocks);
           the memo inflates reported MDEs by x1.5 as a conservatism factor
           (labeled, not estimated).

Run:  python p1/t2a_power_sim.py   (writes p1/t2a_power_results.json)
Seed fixed. numpy+pandas+econlib only.
"""
import json
import sys
import pathlib

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "shared"))
from econlib.did import stacked_did  # noqa: E402

RNG = np.random.default_rng(20260709)
N_STOCKS = 3000
WINDOW = (-4, 4)
G = 4                                   # cohort period: time 0..8, post = t>=4
QUARTERS = list(range(0, 9))
REPS = 150
SUB_T, SUB_C = 150, 250                 # verification subsample (keeps X small)
DELTAS = [0.05, 0.10, 0.20, 0.30, 0.50, 1.00]
THETA_BPS = 25.0
CONSERVATISM = 1.5                     # PRIOR-5 inflation on MDE

FUNDS = [  # (aum $bn, universe cap-rank slice)  PRIOR-2; AUM from events_from_note.csv
    ("DFUS", 5.5, (0, 1000)),
    ("DFAC", 14.4, (0, 2500)),
    ("DFAS", 4.2, (1000, 3000)),
    ("DFAT", 6.6, (800, 2800)),
]
SCENARIOS = {"optimistic": 0.70, "base": 0.85, "pessimistic": 1.00}  # PRIOR-3 gamma


def make_universe():
    caps = np.exp(RNG.normal(np.log(2e9), 1.6, N_STOCKS))          # PRIOR-1
    caps = np.clip(caps, 5e7, 3e12)
    order = np.argsort(-caps)                                       # rank 0 = largest
    return caps[order]


def dose_bps(caps, gamma):
    """Total conversion dose per stock in bps of market cap (PRIOR-3)."""
    dose = np.zeros(N_STOCKS)
    for _, aum_bn, (lo, hi) in FUNDS:
        c = caps[lo:hi]
        w = c ** gamma * np.exp(RNG.normal(0.0, 0.5, hi - lo))
        w = w / w.sum()
        dose[lo:hi] += (aum_bn * 1e9) * w / c * 1e4
    return dose


def sim_once(units_t, units_c, delta):
    """Subsampled panel (units_t treated + units_c controls), econlib convention:
    time 0..8, treated cohort first_treat=G, post = t>=G."""
    ids = list(units_t) + list(units_c)
    n = len(ids)
    is_t = np.r_[np.ones(len(units_t)), np.zeros(len(units_c))]
    unit_col = np.repeat(np.arange(n), len(QUARTERS))
    time_col = np.tile(QUARTERS, n)
    y = RNG.normal(size=n * len(QUARTERS))
    y += delta * (np.repeat(is_t, len(QUARTERS)) * (time_col >= G))
    df = pd.DataFrame({"unit": unit_col, "time": time_col, "y": y,
                       "first_treat": np.repeat(np.where(is_t == 1, G, 0), len(QUARTERS))})
    return stacked_did(df, window=WINDOW)


def analytic_se(n_t, n_c, t_pre=4, t_post=5):
    var_delta = (1.0 / t_pre + 1.0 / t_post)                       # unit Δmean var, sigma=1
    return np.sqrt(var_delta * (1.0 / n_t + 1.0 / n_c))


def kill_switch_n(target_sigma, n_total=N_STOCKS):
    """Smallest treated N (with the rest as controls) whose conservative
    MDE80 still detects target_sigma. Also the symmetric control-side bound."""
    for n in range(2, n_total):
        if 2.80 * analytic_se(n, n_total - n) * CONSERVATISM <= target_sigma:
            return n
    return None


def main():
    caps = make_universe()
    out = {"seed": 20260709, "n_stocks": N_STOCKS, "theta_bps": THETA_BPS,
           "conservatism": CONSERVATISM, "scenarios": {}}
    for name, gamma in SCENARIOS.items():
        d = dose_bps(caps, gamma)
        res = {}
        for th in (10.0, THETA_BPS, 50.0):
            n_t = int((d >= th).sum())
            n_c = N_STOCKS - n_t
            se = analytic_se(max(n_t, 1), max(n_c, 1))
            mde80 = 2.80 * se * CONSERVATISM                       # 1.96 + 0.84
            res[f"theta_{int(th)}bps"] = {
                "n_treated": n_t, "n_control": n_c,
                "median_dose_treated_bps":
                    float(np.median(d[d >= th])) if n_t else None,
                "analytic_mde80_sigma": round(float(mde80), 4)}
        out["scenarios"][name] = res
    out["kill_switch"] = {
        "min_treated_for_0.5sigma": kill_switch_n(0.5),
        "min_treated_for_1.0sigma": kill_switch_n(1.0),
        "note": "smaller side of the treated/control split must exceed this "
                "count for the conservative MDE80 to stay under the target"}
    # simulation verification of the analytic curve at base/theta=25 using the
    # real estimator (subsampled 1:1 scale is unnecessary — run full N, few reps)
    breadth = SCENARIOS["base"]
    d = dose_bps(caps, breadth)
    treated_idx = np.flatnonzero(d >= THETA_BPS)
    control_idx = np.flatnonzero(d < THETA_BPS)
    n_t = min(SUB_T, len(treated_idx))
    units_t = RNG.choice(treated_idx, n_t, replace=False)
    units_c = RNG.choice(control_idx, SUB_C, replace=False)
    ver = {}
    for delta in DELTAS:
        rej = 0
        for _ in range(REPS):
            r = sim_once(units_t, units_c, delta)
            if abs(r["t"]) > 1.96:
                rej += 1
        ver[str(delta)] = round(rej / REPS, 3)
    se_sub = analytic_se(n_t, SUB_C)
    out["verification_subsample"] = {
        "n_treated": int(n_t), "n_control": SUB_C, "reps": REPS,
        "power_by_delta": ver,
        "analytic_se_subsample": round(float(se_sub), 4),
        "note": "econlib stacked_did on a subsampled panel (verifies the "
                "analytic power curve Phi(delta/se - 1.96) at the SUBSAMPLE "
                "size, WITHOUT the x1.5 conservatism; scenario MDEs use the "
                "full treated/control counts analytically)"}
    p = pathlib.Path(__file__).with_name("t2a_power_results.json")
    p.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
