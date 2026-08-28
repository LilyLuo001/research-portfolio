#!/usr/bin/env python3
"""Which abnormal-return benchmark governs which horizon. Frozen v2.1f.

The spec froze exactly one PRIMARY benchmark for the β_h curve. This module is
that rule in executable form, because the failure it prevents is silent: a DGTW
benchmark applied at a 5-minute horizon does not raise, it just returns a number.
The monthly benchmark barely moves inside five minutes, so `AR ≈ raw return` —
the adjustment does nothing while the table says "characteristic-adjusted".

Two rules, both from `p1/t3_spec/变量规格书.md` D-T3-11/17/18/19:

  1. **One benchmark across the whole curve.** The deliverable is the SHAPE of
     β_h over h. If the benchmark changes at some h, a kink there cannot be told
     apart from the benchmark change. A curve whose benchmark varies is not a
     curve.

  2. **DGTW is daily-or-longer only.** Verified against this repo's own spec
     (2-3): DGTW matches portfolios at the start of each calendar MONTH and uses
     monthly value-weighted portfolio returns, sourced from `crsp.msf`. No
     intraday series exists. If one is ever built at matching intraday
     timestamps, it comes back as a NEW robustness proposal — not by relaxing
     this check.

`intraday_market_model` is primary at every horizon. `dgtw` and the two other
variants are robustness and may never be swapped in for the headline.
"""
from __future__ import annotations

# Horizons of the β_h curve, in order. `close` and `+1d` are daily-resolution;
# everything before them is intraday and has no daily benchmark observation.
HORIZONS = ("5m", "15m", "30m", "60m", "close", "+1d")
INTRADAY_HORIZONS = ("5m", "15m", "30m", "60m")
DAILY_OR_LONGER = ("close", "+1d", "+2d", "+5d", "+120d")

PRIMARY = "intraday_market_model"

# benchmark -> the horizons at which it is defined AT ALL.
BENCHMARK_HORIZONS = {
    # r_i(t0→h) − β_i · r_mkt(t0→h), market leg on the SAME intraday timestamps
    # (D-T3-19), β from daily [−250,−21] (D-T3-20).
    "intraday_market_model": HORIZONS + ("+2d", "+5d", "+120d"),
    "intraday_market_beta_one": HORIZONS + ("+2d", "+5d", "+120d"),
    "intraday_market_industry": HORIZONS + ("+2d", "+5d", "+120d"),
    # Monthly characteristic portfolios, monthly VW returns (spec 2-3).
    "dgtw": DAILY_OR_LONGER,
}
ROBUSTNESS = ("intraday_market_beta_one", "intraday_market_industry", "dgtw")


class BenchmarkPolicyError(ValueError):
    """Raised when a benchmark is used at a horizon it is not defined at, or
    when a robustness benchmark is presented as the headline."""


def primary_benchmark(horizon: str) -> str:
    """The benchmark governing the primary β_h at this horizon.

    Constant by construction — see rule 1. It takes the horizon anyway so that
    callers read as "the primary benchmark AT h" and any future attempt to make
    it horizon-dependent has to change this function, in a commit, on purpose.
    """
    if horizon not in BENCHMARK_HORIZONS[PRIMARY]:
        raise BenchmarkPolicyError(
            f"no primary benchmark is defined at horizon {horizon!r}; "
            f"known: {BENCHMARK_HORIZONS[PRIMARY]}")
    return PRIMARY


def assert_benchmark_allowed(benchmark: str, horizon: str) -> None:
    """Refuse a benchmark at a horizon where it does not exist."""
    if benchmark not in BENCHMARK_HORIZONS:
        raise BenchmarkPolicyError(
            f"unknown benchmark {benchmark!r}; known: "
            f"{sorted(BENCHMARK_HORIZONS)}. Name the exact construction — an "
            "unnamed 'characteristic adjustment' is how a daily series ends up "
            "subtracted from a five-minute return.")
    allowed = BENCHMARK_HORIZONS[benchmark]
    if horizon not in allowed:
        extra = ""
        if benchmark == "dgtw" and horizon in INTRADAY_HORIZONS:
            extra = (" DGTW is matched at the start of each calendar month and "
                     "its portfolio returns are monthly (spec 2-3), so there is "
                     "no value at an intraday timestamp. Subtracting it from a "
                     "5-minute return removes a near-constant and leaves AR ≈ "
                     "the raw return, while the table still reads "
                     "'characteristic-adjusted'. Use the intraday market model "
                     "(D-T3-17); keep DGTW for daily-or-longer robustness.")
        raise BenchmarkPolicyError(
            f"benchmark {benchmark!r} is not defined at horizon {horizon!r} "
            f"(defined at: {allowed}).{extra}")


def assert_curve_uses_one_benchmark(by_horizon: dict) -> None:
    """`by_horizon` maps horizon -> benchmark used. Refuse a mixed curve."""
    used = set(by_horizon.values())
    if len(used) > 1:
        raise BenchmarkPolicyError(
            f"the β_h curve mixes benchmarks {sorted(used)} across horizons "
            f"{sorted(by_horizon)}. A kink at the switch point cannot be "
            "distinguished from the switch itself (D-T3-18). Run each benchmark "
            "as a SEPARATE full curve and report one as primary.")
    for h, b in by_horizon.items():
        assert_benchmark_allowed(b, h)


def assert_is_headline(benchmark: str) -> None:
    """Guard the reporting side: robustness may not be presented as headline."""
    if benchmark in ROBUSTNESS:
        raise BenchmarkPolicyError(
            f"{benchmark!r} is a pre-specified ROBUSTNESS benchmark; the "
            f"headline β_h curve is {PRIMARY!r} (D-T3-11, frozen before "
            "estimation). Report it alongside, never instead.")
    if benchmark != PRIMARY:
        raise BenchmarkPolicyError(f"unknown headline benchmark {benchmark!r}")


def _selftest() -> int:
    ok = True

    def expect_raises(label, fn, needle=""):
        nonlocal ok
        try:
            fn()
            print(f"  FAIL {label} did not refuse"); ok = False
        except BenchmarkPolicyError as e:
            good = needle in str(e)
            print(f"  {'ok  ' if good else 'FAIL'} {label} refuses"
                  f"{'' if good else f' but message lacks {needle!r}'}")
            ok = ok and good

    def expect_ok(label, fn):
        nonlocal ok
        try:
            fn()
            print(f"  ok   {label}")
        except BenchmarkPolicyError as e:
            print(f"  FAIL {label}: {e}"); ok = False

    for h in HORIZONS:
        expect_ok(f"primary defined at {h}", lambda h=h: primary_benchmark(h))
    good = len({primary_benchmark(h) for h in HORIZONS}) == 1
    print(f"  {'ok  ' if good else 'FAIL'} one primary across the whole curve")
    ok = ok and good

    for h in INTRADAY_HORIZONS:
        expect_raises(f"dgtw at {h}", lambda h=h: assert_benchmark_allowed("dgtw", h),
                      "no value at an intraday timestamp")
    for h in ("close", "+1d", "+120d"):
        expect_ok(f"dgtw at {h}", lambda h=h: assert_benchmark_allowed("dgtw", h))

    expect_raises("mixed curve", lambda: assert_curve_uses_one_benchmark(
        {"5m": "intraday_market_model", "close": "dgtw"}), "mixes benchmarks")
    expect_ok("uniform curve", lambda: assert_curve_uses_one_benchmark(
        {h: PRIMARY for h in HORIZONS}))

    expect_raises("dgtw as headline", lambda: assert_is_headline("dgtw"),
                  "ROBUSTNESS")
    expect_raises("beta-one as headline",
                  lambda: assert_is_headline("intraday_market_beta_one"),
                  "ROBUSTNESS")
    expect_ok("primary as headline", lambda: assert_is_headline(PRIMARY))
    expect_raises("unnamed benchmark",
                  lambda: assert_benchmark_allowed("characteristic_adjusted", "5m"),
                  "Name the exact construction")

    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
