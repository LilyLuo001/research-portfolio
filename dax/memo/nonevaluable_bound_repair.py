"""Show that the v3 non-evaluable upper bound inverts, and repair it.

`onet_benchmark_v3_design_20260823.json` sets

    lower_bound_contribution: zero_crossing_mass
    upper_bound_contribution: all_non_evaluable_mass_crosses
    center: None

Writing `B` for an occupation's evaluable task-mass share and `E` for the
crossing rate among that mass, those are `B*E` and `B*E + (1 - B)`. Setting
`center` to None is right -- there is no warrant for a point estimate. The
lower rule is also fine. The upper rule is not: rewritten it is

    upper = 1 - B*(1 - E)

which is *decreasing* in `B` whenever `E < 1`. The least-evaluable occupations
receive the highest upper-bound exposure, so the upper index is close to a
monotone transform of the manual/interpersonal share. Regressing on it does
not bound the coefficient of interest; it estimates the coefficient on a
roughly inverted treatment.

The repair keeps the honesty and drops the inversion. Under the design memo's
continuous-dose design the regressor is a level with occupation and month
fixed effects, so the time-invariant part of the unmeasured mass is absorbed
and never needs identifying. Only its *change* matters. Writing
`DAX_ot = B_o*E_ot + (1 - B_o)*N_ot` and `kappa = dN/dE`,

    dDAX_ot(kappa) = dE_ot * [ B_o + kappa*(1 - B_o) ]

The bracket is weakly increasing in `B_o` for every kappa in [0, 1], so the
cross-occupation ordering never inverts. kappa = 0 is the digitally identified
estimand; kappa = 1 has all task mass crossing at the digital rate. kappa > 1
would mean non-evaluable mass crosses faster than evaluable mass, which no
event in the registry could produce, so 1 is the default cap.

Run: python dax/memo/nonevaluable_bound_repair.py
"""

from __future__ import annotations

KAPPAS = (0.0, 0.25, 0.5, 0.75, 1.0)


def level_bounds(b: float, e: float) -> tuple[float, float]:
    """The v3 rule as written."""
    return b * e, b * e + (1.0 - b)


def dose_multiplier(b: float, kappa: float) -> float:
    """The proposed replacement: the multiplier on the measured dose change."""
    return b + kappa * (1.0 - b)


def upper_bound_inverts(shares: list[float], e: float) -> bool:
    """True when a lower evaluable share yields a higher upper bound."""
    ups = [level_bounds(b, e)[1] for b in sorted(shares)]
    return any(ups[i] < ups[i + 1] for i in range(len(ups) - 1)) is False and len(
        {round(u, 12) for u in ups}
    ) > 1


def multiplier_preserves_order(shares: list[float], kappa: float) -> bool:
    """True when the dose multiplier is weakly increasing in the evaluable share."""
    ms = [dose_multiplier(b, kappa) for b in sorted(shares)]
    return all(ms[i] <= ms[i + 1] + 1e-12 for i in range(len(ms) - 1))


def main() -> int:
    shares = [0.05, 0.15, 0.30, 0.50, 0.80]
    e = 0.40
    print("v3 rule as written (E = %.2f):" % e)
    print(f"{'B':>8}{'lower':>10}{'upper':>10}")
    for b in shares:
        lo, up = level_bounds(b, e)
        print(f"{b:>8.2f}{lo:>10.3f}{up:>10.3f}")
    print(f"\nupper bound inverts the ordering: {upper_bound_inverts(shares, e)}")

    print("\nrepair -- dose multiplier [B + kappa(1-B)]:")
    print(f"{'B':>8}" + "".join(f"{'k=%.2f' % k:>9}" for k in KAPPAS))
    for b in shares:
        print(f"{b:>8.2f}" + "".join(f"{dose_multiplier(b, k):>9.3f}" for k in KAPPAS))
    ok = all(multiplier_preserves_order(shares, k) for k in KAPPAS)
    print(f"\nordering preserved at every kappa in [0, 1]: {ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
