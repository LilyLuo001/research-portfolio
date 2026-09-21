"""Deterministic logical tests for V2 interfaces; no empirical inputs or network."""
import hashlib
import json
from pathlib import Path

import numpy as np

from estimator import (InputRejected, PairedQuote, composition_decomposition,
                       fieller_set, fixed_common_support_weights,
                       fit_joint_standardized_slopes, paired_response,
                       ratio_contrast_confidence_set)

SEED = 20260921


def rejected(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except InputRejected:
        return True
    return False


def main():
    checks = []
    def check(name, passed, details):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    # All four fixed F* cells have both groups and two issuers. Issuer A has
    # twice the events of B; every event has two ETF paired rows.
    rows = []
    for cell in ("lowC", "highC"):
        for group in ("TOP", "REST"):
            for issuer, count in (("A", 2), ("B", 1)):
                for k in range(count):
                    rows.extend({"cell": cell, "group": group, "issuer_id": issuer,
                                 "event_id": f"{cell}-{group}-{issuer}-{k}", "etf_id": etf}
                                for etf in ("ETF1", "ETF2"))
    top_rows = [r for r in rows if r["group"] == "TOP"]
    target = {(c, g): {"A": .5, "B": .5} for c in ("lowC", "highC") for g in ("TOP", "REST")}
    event_target = {(r["cell"], r["group"], r["event_id"]): {"ETF1": .5, "ETF2": .5} for r in rows}
    weights = fixed_common_support_weights(top_rows, fstar_cells=("lowC", "highC"), groups=("TOP",), issuer_weights=target, event_etf_weights=event_target)
    a_mass = sum(w for w, r in zip(weights, top_rows) if r["cell"] == "lowC" and r["issuer_id"] == "A")
    b_mass = sum(w for w, r in zip(weights, top_rows) if r["cell"] == "lowC" and r["issuer_id"] == "B")
    check("fixed_fstar_event_total_then_issuer_weighting", np.isclose(weights.sum(), 1) and np.isclose(a_mass, b_mass),
          {"weights_sum": float(weights.sum()), "A_mass": float(a_mass), "B_mass": float(b_mass),
           "interpretation": "PROPOSED_CONDITIONAL_LINEAR_PROJECTION_NOT_ISSUER_MEAN"})
    missing = top_rows[:-1]
    check("common_support_failure_rejected", rejected(fixed_common_support_weights, missing, fstar_cells=("lowC", "highC"), groups=("TOP",), issuer_weights=target, event_etf_weights=event_target), {})
    check("top_rest_pooling_rejected", rejected(fixed_common_support_weights, rows, fstar_cells=("lowC", "highC"), groups=("TOP", "REST"), issuer_weights=target, event_etf_weights=event_target), {})

    q = PairedQuote(100., 101., 102., True, True, True, (0., 0.), (2., 2.), (4., 4.))
    paired = paired_response(q, q, actual_basket=True, basket_kind="ACTUAL_HOLDINGS", quote_side="mid")
    check("paired_actual_basket_response", np.isclose(paired["etf_h"], paired["basket_h"]), paired)
    check("proxy_basket_rejected", rejected(paired_response, q, q, actual_basket=False, basket_kind="PCF", quote_side="mid"), {})
    overlapping = PairedQuote(100., 101., 102., True, True, True, (0., 1.), (.5, 2.), (4., 4.))
    check("uncertain_clock_order_rejected", rejected(paired_response, overlapping, q, actual_basket=True, basket_kind="ACTUAL_HOLDINGS", quote_side="mid"), {})
    different_target = PairedQuote(100., 101., 102., True, True, True, (0., 0.), (3., 3.), (4., 4.))
    check("cross_market_evaluation_interval_rejected", rejected(paired_response, q, different_target, actual_basket=True, basket_kind="ACTUAL_HOLDINGS", quote_side="mid"), {})

    rng = np.random.default_rng(SEED)
    events, copies = 12, 3
    z0 = rng.normal(size=events)
    z = np.repeat(z0, copies)
    common = np.repeat(rng.normal(scale=.25, size=events), copies)
    y = np.column_stack([.8*z + common + rng.normal(scale=.01, size=len(z)),
                         .3*z + common + rng.normal(scale=.01, size=len(z)),
                         1.0*z + common + rng.normal(scale=.01, size=len(z)),
                         1.0*z + common + rng.normal(scale=.01, size=len(z))])
    event_ids = np.repeat([f"e{k}" for k in range(events)], copies)
    cell_ids = np.repeat(["lowC" if k < events//2 else "highC" for k in range(events)], copies)
    result = fit_joint_standardized_slopes(z, y, np.repeat(1/len(z), len(z)), event_ids,
                                           cell_ids=cell_ids, fstar_cells=("lowC", "highC"),
                                           standardization_cell_weights={"lowC": .5, "highC": .5})
    cov = np.asarray(result["joint_covariance"])
    # The deliberately duplicated common shock makes cluster covariance exceed
    # the row-IID analogue for the first response in this synthetic fixture.
    X = np.column_stack([np.ones(len(z)), z]) / np.sqrt(len(z))
    residual = y / np.sqrt(len(z)) - X @ np.linalg.lstsq(X, y / np.sqrt(len(z)), rcond=None)[0]
    iid00 = np.sum(((X @ np.linalg.inv(X.T @ X))[:, 1] * residual[:, 0]) ** 2)
    check("joint_covariance_psd_and_cluster_ordering", np.linalg.eigvalsh(cov).min() >= -1e-10 and cov[0, 0] > iid00,
          {"min_eigenvalue": float(np.linalg.eigvalsh(cov).min()), "event_cluster_var": float(cov[0, 0]), "row_iid_var": float(iid00)})
    common_fit = {"cell_ids": ["lowC", "highC"], "fstar_cells": ("lowC", "highC"), "standardization_cell_weights": {"lowC": .5, "highC": .5}}
    check("nonfinite_and_nonpsd_inputs_rejected", rejected(fieller_set, 0., 1., [[1., 2.], [2., 1.]]) and rejected(fit_joint_standardized_slopes, [0., np.nan], [[0., 0., 0., 0.]]*2, [.5, .5], ["e", "e"], **common_fit), {})
    check("repeat_event_dependence_required", rejected(fit_joint_standardized_slopes, z, y, np.repeat(1/len(z), len(z)), list(range(len(z))), cell_ids=cell_ids, fstar_cells=("lowC", "highC"), standardization_cell_weights={"lowC": .5, "highC": .5}), {})

    # Unequal x variation proves why F* requires cell-specific slopes: a pooled
    # regression would x^2-weight the high-variance cell rather than average .8/.2.
    x2_event = np.array([-.2, .2, -.1, .1, -2., 2., -1., 1.])
    x2 = np.repeat(x2_event, 2)
    c2 = np.repeat(["lowC"]*4 + ["highC"]*4, 2)
    e2 = np.repeat([f"s{k}" for k in range(8)], 2)
    etf_slope = np.where(c2 == "lowC", .8, .2)
    y2 = np.column_stack([etf_slope*x2, .1*x2, x2, x2])
    standard = fit_joint_standardized_slopes(x2, y2, np.repeat(1/len(x2), len(x2)), e2,
                                              cell_ids=c2, fstar_cells=("lowC", "highC"), standardization_cell_weights={"lowC": .5, "highC": .5})
    pooled = np.dot(x2, y2[:, 0]) / np.dot(x2, x2)
    check("fixed_fstar_cell_standardization_not_pooled_x2_weighting", np.isclose(standard["slopes"][0], .5) and not np.isclose(pooled, .5),
          {"fixed_Fstar_slope": standard["slopes"][0], "pooled_x2_weighted_slope": float(pooled)})

    weak = fieller_set(.05, 0., [[.01, 0.], [0., .01]])
    check("weak_denominator_retains_unbounded_set", weak["kind"] != "BOUNDED", weak)
    contrast = ratio_contrast_confidence_set()
    check("joint_ratio_contrast_not_marginal_ci_subtraction", contrast["status"] == "NOT_IMPLEMENTED" and "not subtracted" in contrast["reason"], contrast)
    dec = composition_decomposition([.2, .8], [.6, .4], [.6, .1], [.6, .1])
    check("composition_change_separated_from_within_response", np.isclose(dec["within_response_change"], 0) and np.isclose(dec["total_change"], dec["composition_change"]), dec)
    check("unsupported_composition_rejected", rejected(composition_decomposition, [.2, .7], [.6, .4], [.1, .1], [.1, .1]), {})

    output = {"status": "SYNTHETIC_LOGIC_TESTS_ONLY", "seed": SEED, "checks": checks,
              "passed": sum(c["passed"] for c in checks), "total": len(checks),
              "empirical_data_read": False, "empirical_power": "NOT_RUN",
              "production_ready": "NOT_CLAIMED", "parameters": "PROPOSED_NOT_FROZEN",
              "code_sha256": hashlib.sha256(Path(__file__).with_name("estimator.py").read_bytes()).hexdigest()}
    out_path = Path(__file__).with_name("SYNTHETIC_TEST_RESULTS.json")
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": output["passed"], "total": output["total"], "output": str(out_path)}))
    if output["passed"] != output["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
