# SH-econlib — continuous-dose DiD estimator

**Seat D** (owns `shared/`). Raised by seat C from the P1 roadmap, 2026-08-19.
Blocks **P1-T5** and, on the same argument, **DAX-W5**.

---

## Why this exists

P1's treatment variable `ConvExp` is a **continuous dose**, and `docs/Project_1.md`
§T5 asks for "Callaway-Sant'Anna 与 Sun-Abraham 在连续处理强度下的适配方案". The
shared toolkit cannot do it:

```
callaway_santanna(df, y, unit, time, first_treat)
stacked_did(df, y, unit, time, first_treat, window)
twfe_did(df, y, unit, time, treat)
```

All three are binary / staggered-adoption estimators keyed on `first_treat`.
`grep -rn "dose\|intensity\|continuous" shared/econlib/` returns nothing.

**So T5 is not implementable today even with WRDS data in hand.** This is a code
block, not a data block, which is why it can be cleared now.

DAX has the same shape — its D1 amendment moved the primary specification to a
continuous cumulative dose — so one estimator serves both projects, which is the
whole argument for econlib living in `shared/`.

## The econometrics this must respect

Reference: Callaway, Goodman-Bacon & Sant'Anna, *Difference-in-Differences with a
Continuous Treatment* ([NBER w32117](https://www.nber.org/papers/w32117),
[arXiv 2107.02637](https://arxiv.org/abs/2107.02637)).

The result that constrains the API:

- Under **standard** parallel trends, `ATT(d)` is identified *level by level*, but
  **comparisons across dose levels are contaminated by selection bias** arising
  from treatment-effect heterogeneity across dose groups.
- Identifying a **dose-response** parameter — `ACRT(d)`, the derivative of
  `ATT(d)` — requires **strong parallel trends**: the average change from
  untreated to dose *d* must be the same for all units as for those who actually
  received dose *d*.
- Even under strong parallel trends, the TWFE coefficient weights causal
  responses differently from the dose distribution among the treated, so the TWFE
  number is not the estimand anyone wants.

**Design consequence, and the reason this is not just "add a `dose=` argument":**
the API must make the user *name* which assumption they are buying. An estimator
that silently returns a dose-response slope under standard parallel trends is
precisely the failure mode the paper warns about, and it would be invisible in
the output.

## Interface

```python
def continuous_dose_did(
    df, *, y="y", unit="unit", time="time", dose="dose", first_treat="first_treat",
    estimand="att",            # "att" | "acrt"
    parallel_trends="standard", # "standard" | "strong"
    dose_bins=None,            # None = use observed dose levels; int = quantile bins
) -> dict
```

Returned dict carries, at minimum:

| key | meaning |
|---|---|
| `estimand` | echoed |
| `parallel_trends` | echoed — must appear in every downstream table |
| `att_by_dose` | DataFrame: dose level/bin, ATT, SE, n_treated, n_control |
| `overall_att` | dose-weighted aggregate + SE |
| `acrt` | present **only** when `estimand="acrt"` |
| `warnings` | list of strings; never silent |

### Hard requirements

1. **`estimand="acrt"` with `parallel_trends="standard"` must raise**, with a
   message naming strong parallel trends and citing w32117. This is the whole
   point of the interface. Do not downgrade it to a warning.
2. **Never return a TWFE dose coefficient as if it were ACRT.** If a TWFE
   comparison is offered at all, label it `twfe_reference` and attach a warning
   that its weights differ from the treated dose distribution.
3. **Zero-dose units are the control group.** Units with `dose == 0` are never
   "treated with a small dose". A sample with no zero-dose units cannot identify
   `ATT(d)` — raise.
4. **Never-treated vs not-yet-treated controls** must be selectable and recorded
   in the output, same as the existing `callaway_santanna`.
5. **numpy + pandas only** — the package constraint. No new dependencies.
6. **Seeded.** Any bootstrap takes an explicit seed and records it.

## Tests seat D should write

Hand-computable synthetic worlds, in the style of the existing econlib tests.

| # | World | Expectation |
|---|---|---|
| 1 | Homogeneous effect `τ` at every dose | `ATT(d) = τ` for all d; `ACRT = 0` |
| 2 | Linear response `τ(d) = 2d`, no selection | `ACRT ≈ 2` under strong PT |
| 3 | Linear response **with** dose-correlated selection | ACRT under standard PT is biased; **the call raises**, so the test asserts the raise |
| 4 | No zero-dose units | raises |
| 5 | Staggered adoption + continuous dose | ATT(d) recovered per cohort, aggregated correctly |
| 6 | Single dose level only | degrades to binary DiD and says so in `warnings` |
| 7 | Dose with an extreme outlier | `dose_bins` quantile path is stable; unbinned path warns |

World 3 is the important one: it is the paper's central point, and a test that
only covers well-behaved worlds would let the bias through.

## Acceptance

- `python -m pytest shared/econlib/tests -q` green.
- `econlib_smoke` contract passes.
- `shared/econlib/__init__.py` docstring and `__version__` updated.
- The P1 T5 blueprint can then name the estimator and its assumption in one line.

## What seat C is doing in the meantime

Reporting `ATT` by **dose tercile** as the primary P1 specification, with the
continuous version demoted to robustness pending this estimator. That fallback is
already forced by a separate finding — the ≥1% dose tier holds only 24 treated
stocks against a power floor of 33 (`p1/t1_reconcile/`), so the fine-grained dose
grid is underpowered regardless of which estimator is available.

**This brief does not depend on that decision.** Whichever way P1 goes, DAX still
needs the estimator, and P1's robustness arm still needs it.
