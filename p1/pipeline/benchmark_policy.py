#!/usr/bin/env python3
"""Which abnormal-return benchmark and formula govern which horizon. v2.1f/g.

The spec froze exactly one PRIMARY benchmark AND one formula for the β_h curve.
This module is that rule in executable form, because every failure it prevents is
silent: a monthly benchmark applied at a 5-minute horizon does not raise, it just
returns a number that is ≈ the raw return, while the table says
"characteristic-adjusted"; a daily α̂ subtracted from a 5-minute return does not
raise either.

Four rules, from `p1/t3_spec/变量规格书.md` D-T3-11/17/18/19/22/25-28:

  1. **One benchmark across the whole curve.** The deliverable is the SHAPE of
     β_h over h. If the benchmark changes at some h, a kink there cannot be told
     apart from the benchmark change. A curve whose benchmark varies is not a
     curve.

  2. **DGTW is restricted to the frequency the data actually supports.**
     Verified against this repo's own spec (2-3): DGTW matches portfolios at the
     start of each calendar MONTH and uses MONTHLY value-weighted portfolio
     returns from `crsp.msf`. That supports monthly-resolution horizons and
     nothing finer — not intraday, and **not daily either**.

     An earlier revision of this file said DGTW "remains the daily/[0,+120]
     robustness benchmark". That was an assertion about data nobody had checked:
     a daily DGTW path needs a DAILY benchmark-portfolio return series, and this
     repo has none. `crsp.ermport` is the candidate and is unverified here (no
     egress). So `dgtw_daily` exists as a name with an EMPTY horizon set, gated
     on DGTW_DAILY_VERIFICATION, and until that lands the daily [0,+120] path is
     market-model adjusted and must not be called characteristic-adjusted.

  3. **One formula, not just one benchmark** (D-T3-22). The primary is
     `AR^h = R^h − β̂_i · R^h_m`, **with no intercept**. α̂ from the daily
     [−250,−21] model is a per-trading-day drift: subtracting it unscaled at 5m
     removes about 78 times too much, and scaling it needs an intraday
     drift-allocation convention this project never pre-specified. Dropping α is
     the only option that keeps one formula at every h, which rule 1 requires.
     The scaled-alpha variant is a named robustness, applied uniformly or not at
     all.

  4. **One market proxy across both legs** (D-T3-25..28). β̂ and the
     event-window market leg must be the SAME traded instrument, on the same
     quote convention and the same session clock. Estimating β̂ against a CRSP
     value-weighted index and applying it to an SPY intraday return is two
     different market portfolios in one formula — and it yields a plausible
     number, not an error. Frozen as one bundle in MARKET_PROXY; the overnight
     gap is excluded from BOTH legs identically (PROXY_OPEN_GAP_RULE).

`beta_adjusted_market` is primary at every horizon — named for what it IS, a
beta-adjusted market abnormal return, not a "market model", because no intercept
is subtracted (rule 3) and the paper must not imply otherwise. Everything in
ROBUSTNESS is reported alongside and may never be swapped in for the headline.
"""
from __future__ import annotations

# Horizons of the β_h curve, in order. `close` and `+1d` are daily-resolution;
# everything before them is intraday and has no daily benchmark observation.
HORIZONS = ("5m", "15m", "30m", "60m", "close", "+1d")
INTRADAY_HORIZONS = ("5m", "15m", "30m", "60m")
DAILY_OR_LONGER = ("close", "+1d", "+2d", "+5d", "+120d")

PRIMARY = "beta_adjusted_market"

# benchmark -> the horizons at which it is defined AT ALL.
BENCHMARK_HORIZONS = {
    # AR^h = R^h − β̂_i · R^h_m. NO INTERCEPT (D-T3-22): α̂ is a per-trading-day
    # drift, and the market leg is on the SAME timestamps as the stock leg
    # (D-T3-19), β̂ from the daily [−250,−21] model (D-T3-20).
    "beta_adjusted_market": HORIZONS + ("+2d", "+5d", "+120d"),
    # Same formula plus a horizon-scaled intercept α̂·(h/D), applied uniformly.
    "beta_adjusted_market_scaled_alpha": HORIZONS + ("+2d", "+5d", "+120d"),
    "beta_one_market_adjusted": HORIZONS + ("+2d", "+5d", "+120d"),
    "beta_adjusted_market_industry": HORIZONS + ("+2d", "+5d", "+120d"),
    # Spec 2-3 builds DGTW from monthly characteristic portfolios with MONTHLY
    # value-weighted returns. That supports monthly-resolution horizons and
    # nothing finer.
    "dgtw_monthly": ("+1m", "+3m", "+6m"),
    # A DAILY DGTW benchmark-portfolio series would support the daily path — but
    # this repo does not have one and has not verified that any purchasable
    # table supplies it. Empty until that verification lands; see
    # DGTW_DAILY_VERIFICATION below.
    "dgtw_daily": (),
}
ROBUSTNESS = ("beta_adjusted_market_scaled_alpha", "beta_one_market_adjusted",
              "beta_adjusted_market_industry", "dgtw_monthly", "dgtw_daily")

# What has to be true before `dgtw_daily` may be used at all. Written as a
# question about data, not a preference: the previous revision of this file
# asserted DGTW "remains the daily/[0,+120] robustness benchmark" without
# checking that a daily benchmark-portfolio return series exists anywhere in
# reach. It may well exist — but "may well" is not a locator (meta-rule 1).
DGTW_DAILY_VERIFICATION = (
    "NEED_HUMAN: confirm, against the WRDS variable documentation or the "
    "Wermers distribution, (a) that a DAILY DGTW benchmark-portfolio return "
    "series exists, (b) which table/file supplies it, and (c) its coverage "
    "period. `crsp.ermport` is the candidate and is UNVERIFIED here — this "
    "container has no egress, so its frequency and contents cannot be checked. "
    "Until then the daily [0,+120] path is market-model adjusted and must NOT "
    "be described as characteristic-adjusted.")


class BenchmarkPolicyError(ValueError):
    """Raised when a benchmark is used at a horizon it is not defined at, or
    when a robustness benchmark is presented as the headline."""


class ProxyIncoherent(BenchmarkPolicyError):
    """Raised when β̂ and the event-window market leg refer to different
    economic market proxies."""


# --------------------------------------------------------------------------- #
# The market proxy — instrument, quote convention, clock and β̂ source, frozen  #
# TOGETHER (D-T3-25..28, v2.1h). Freezing them apart is what lets an           #
# incoherent pair through: a CRSP value-weighted-index β̂ applied to an SPY     #
# intraday return is two different market portfolios in one formula, and it    #
# produces a number rather than an error.                                      #
# --------------------------------------------------------------------------- #
MARKET_PROXY = {
    # ONE traded instrument, used for BOTH legs. CRSP's vwretd cannot be the
    # intraday leg — like DGTW it has no intraday value — so the intraday leg
    # must be a traded instrument, and therefore so must the β̂ estimation
    # series. Pre-specified: SPY.
    "instrument": "SPY",
    # Same convention as the stock leg (D-T3-13): trade prices bounce between
    # bid and ask, which at 5m is a large share of the signal.
    "quote_convention": "midquote",
    # Regular trading hours only. The overnight gap has no quotes, so it is
    # excluded from BOTH legs identically — never from one only.
    "session": "RTH",
    "rth_open_et": "09:30",
    "rth_close_et": "16:00",
    # β̂ comes from the SAME instrument's daily returns over [−250,−21].
    "beta_estimation_instrument": "SPY",
    "beta_estimation_window": (-250, -21),
    "beta_estimation_return": "close_to_close",
}

# Named so a reviewer can see what was NOT chosen and why.
REJECTED_PROXIES = {
    "crsp_vwretd": (
        "CRSP value-weighted index. No intraday value exists, so it cannot be "
        "the event-window leg; using it for β̂ while the intraday leg is a "
        "traded ETF puts two different market portfolios in one formula."),
    "crsp_ewretd": "as crsp_vwretd, and equal-weighted on top of it.",
}

PROXY_OPEN_GAP_RULE = (
    "Both legs start at the SAME timestamp, and the overnight gap is in "
    "neither. Pre-open announcement: h runs from that day's first RTH midquote. "
    "After-close announcement: from the NEXT day's first RTH midquote. "
    "Intraday announcement: from the announcement timestamp. The `close` "
    "horizon ends at that session's actual close — 13:00 ET on an early-close "
    "day, not 16:00. Including the gap in the stock leg but not the market leg "
    "(or the reverse) puts an unhedged overnight move into AR^h, and it does "
    "not raise.")


def assert_proxy_coherent(beta_instrument: str, market_leg_instrument: str,
                          *, quote_convention: str = None,
                          session: str = None) -> None:
    """The β̂ series and the event-window market leg must be ONE proxy.

    This is the check the owner named: estimating β̂ against a CRSP
    value-weighted index and then applying it to an SPY intraday return mixes
    two market portfolios. Nothing downstream notices — β̂ is a plausible
    number, the intraday return is a plausible number, and AR^h comes out
    plausible too.
    """
    if beta_instrument != market_leg_instrument:
        why = REJECTED_PROXIES.get(beta_instrument) or REJECTED_PROXIES.get(
            market_leg_instrument) or ""
        raise ProxyIncoherent(
            f"β̂ is estimated against {beta_instrument!r} but the event-window "
            f"market leg is {market_leg_instrument!r}. These must be the SAME "
            f"economic proxy (D-T3-25); frozen: {MARKET_PROXY['instrument']!r}. "
            + (f"Note: {why}" if why else ""))
    if beta_instrument != MARKET_PROXY["instrument"]:
        raise ProxyIncoherent(
            f"proxy {beta_instrument!r} is coherent with itself but is not the "
            f"frozen instrument {MARKET_PROXY['instrument']!r}. Changing it is a "
            "spec change (D-T3-25), not a runtime option.")
    if quote_convention is not None and quote_convention != MARKET_PROXY["quote_convention"]:
        raise ProxyIncoherent(
            f"market leg uses {quote_convention!r} but the stock leg and the "
            f"frozen convention are {MARKET_PROXY['quote_convention']!r} "
            "(D-T3-26). Mixing trade prices into one leg and midquotes into the "
            "other puts bid-ask bounce into AR^h at exactly the horizons where "
            "it is largest.")
    if session is not None and session != MARKET_PROXY["session"]:
        raise ProxyIncoherent(
            f"session {session!r} is not the frozen {MARKET_PROXY['session']!r} "
            f"(D-T3-27). {PROXY_OPEN_GAP_RULE}")


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
        if benchmark == "dgtw_monthly":
            extra = (" DGTW is matched at the start of each calendar month and "
                     "its portfolio returns are MONTHLY (spec 2-3), so it has no "
                     "value at a finer timestamp. Subtracting a monthly return "
                     "from an intraday or daily one removes a near-constant: AR "
                     "comes out ≈ the raw return while the table still reads "
                     "'characteristic-adjusted'.")
        if benchmark == "dgtw_daily":
            extra = " " + DGTW_DAILY_VERIFICATION
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

    for h in INTRADAY_HORIZONS + ("close", "+1d", "+120d"):
        expect_raises(f"dgtw_monthly at {h}",
                      lambda h=h: assert_benchmark_allowed("dgtw_monthly", h),
                      "portfolio returns are MONTHLY")
    expect_ok("dgtw_monthly at +3m",
              lambda: assert_benchmark_allowed("dgtw_monthly", "+3m"))
    for h in ("close", "+1d", "+120d"):
        expect_raises(f"dgtw_daily at {h} is gated on verification",
                      lambda h=h: assert_benchmark_allowed("dgtw_daily", h),
                      "NEED_HUMAN")
    expect_raises("bare 'dgtw' is no longer a benchmark name",
                  lambda: assert_benchmark_allowed("dgtw", "+1d"),
                  "Name the exact construction")

    expect_raises("mixed curve", lambda: assert_curve_uses_one_benchmark(
        {"5m": "beta_adjusted_market", "close": "beta_one_market_adjusted"}),
        "mixes benchmarks")
    expect_ok("uniform curve", lambda: assert_curve_uses_one_benchmark(
        {h: PRIMARY for h in HORIZONS}))

    expect_raises("dgtw_monthly as headline",
                  lambda: assert_is_headline("dgtw_monthly"), "ROBUSTNESS")
    expect_raises("scaled-alpha as headline",
                  lambda: assert_is_headline("beta_adjusted_market_scaled_alpha"),
                  "ROBUSTNESS")
    expect_raises("beta-one as headline",
                  lambda: assert_is_headline("beta_one_market_adjusted"),
                  "ROBUSTNESS")
    expect_ok("primary as headline", lambda: assert_is_headline(PRIMARY))
    expect_raises("unnamed benchmark",
                  lambda: assert_benchmark_allowed("characteristic_adjusted", "5m"),
                  "Name the exact construction")

    # --- market proxy coherence (D-T3-25..28) ---
    expect_ok("frozen proxy on both legs",
              lambda: assert_proxy_coherent("SPY", "SPY",
                                            quote_convention="midquote",
                                            session="RTH"))
    expect_raises("CRSP beta + SPY intraday leg",
                  lambda: assert_proxy_coherent("crsp_vwretd", "SPY"),
                  "SAME economic proxy")
    expect_raises("SPY beta + CRSP leg",
                  lambda: assert_proxy_coherent("SPY", "crsp_vwretd"),
                  "SAME economic proxy")
    expect_raises("coherent but not the frozen instrument",
                  lambda: assert_proxy_coherent("IVV", "IVV"),
                  "not the frozen instrument")
    expect_raises("trade prices on the market leg",
                  lambda: assert_proxy_coherent("SPY", "SPY",
                                                quote_convention="last_trade"),
                  "bid-ask bounce")
    expect_raises("extended hours",
                  lambda: assert_proxy_coherent("SPY", "SPY", session="ETH"),
                  "overnight gap")
    good = (MARKET_PROXY["instrument"]
            == MARKET_PROXY["beta_estimation_instrument"])
    print(f"  {'ok  ' if good else 'FAIL'} the frozen bundle is self-coherent")
    ok = ok and good

    print("\nSELFTEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
